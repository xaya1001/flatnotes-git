#!/usr/bin/env python3
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from playwright.sync_api import expect, sync_playwright
except ModuleNotFoundError:
    print(
        "Playwright is required for e2e tests. Install it for this Python "
        "environment with: python3 -m pip install playwright && python3 -m playwright install chromium",
        file=sys.stderr,
    )
    raise


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
NOTE_TITLE = "E2E Fork Feature Smoke"
NOTE_FILE = DATA_DIR / f"{NOTE_TITLE}.md"
BASE_URL = "http://127.0.0.1:8080"
API_URL = "http://127.0.0.1:8000"
RAIL_SELECTOR = "xpath=//div[@data-right-tool-rail]"
RAIL_OPEN_CHECK = """el => {
    const matrix = new DOMMatrixReadOnly(getComputedStyle(el).transform);
    return matrix.m41 <= -479;
}"""
RAIL_CLOSED_CHECK = """el => {
    const matrix = new DOMMatrixReadOnly(getComputedStyle(el).transform);
    return Math.abs(matrix.m41) < 1;
}"""

NOTE_CONTENT = """# Root

## Child

### Grandchild

```mermaid
graph TD
  A[Start] --> B[Done]
```

Body for copy checks.
"""


class ManagedProcess:
    def __init__(self, name, command, env=None):
        self.name = name
        self.command = command
        self.env = env
        self.process = None

    def start(self):
        self.process = subprocess.Popen(
            self.command,
            cwd=ROOT,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )

    def stop(self):
        if not self.process or self.process.poll() is not None:
            return
        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            self.process.wait(timeout=5)


def require_command(command):
    if shutil.which(command) is None:
        raise RuntimeError(f"Required command not found: {command}")


def write_seed_note():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NOTE_FILE.write_text(NOTE_CONTENT, encoding="utf-8")
    if not (DATA_DIR / ".git").exists():
        subprocess.run(["git", "init", "-b", "main"], cwd=DATA_DIR, check=True)
        subprocess.run(
            ["git", "config", "user.name", "flatnotes-e2e"],
            cwd=DATA_DIR,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "e2e@flatnotes.local"],
            cwd=DATA_DIR,
            check=True,
        )


def wait_for_url(url, timeout=45):
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def backend_env():
    env = os.environ.copy()
    env.update(
        {
            "PIPENV_DONT_LOAD_ENV": "1",
            "FLATNOTES_PATH": str(DATA_DIR),
            "FLATNOTES_AUTH_TYPE": "none",
            "FLATNOTES_GIT_ENABLED": "true",
            "FLATNOTES_GIT_AUTO_INIT": "true",
            "FLATNOTES_GIT_REMOTE_NAME": "origin",
            "FLATNOTES_GIT_DEFAULT_BRANCH": "main",
            "FLATNOTES_GIT_COMMIT_USER_NAME": "flatnotes-e2e",
            "FLATNOTES_GIT_COMMIT_USER_EMAIL": "e2e@flatnotes.local",
            "FLATNOTES_FRONTEND_IMAGE_COMPRESSION_ENABLED": "true",
            "FLATNOTES_FRONTEND_IMAGE_COMPRESSION_QUALITY": "0.7",
            "FLATNOTES_FRONTEND_IMAGE_MAX_WIDTH": "1280",
        }
    )
    return env


def run_browser_checks():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        page.goto(
            f"{BASE_URL}/note/{urllib.parse.quote(NOTE_TITLE)}",
            wait_until="networkidle",
        )

        config = page.evaluate("""async () => {
                const response = await fetch('/api/config');
                return response.json();
            }""")
        assert config["flatnotesGitEnabled"] is True
        assert config["frontendImageCompressionEnabled"] is True
        assert config["frontendImageCompressionQuality"] == 0.7
        assert config["frontendImageMaxWidth"] == 1280

        git_button = page.locator("button[title*='Branch']")
        outline_button = page.get_by_role("button", name="Outline")
        rail = page.locator(RAIL_SELECTOR).first

        expect(git_button).to_be_visible()
        expect(outline_button).to_be_visible()

        git_button.click()
        expect(page.get_by_role("heading", name="Git Sync")).to_be_visible()
        page.wait_for_function(RAIL_OPEN_CHECK, arg=rail.element_handle())
        open_transform = rail.evaluate("el => getComputedStyle(el).transform")

        git_button.click()
        expect(page.get_by_role("heading", name="Git Sync")).to_be_visible()
        page.wait_for_function(RAIL_OPEN_CHECK, arg=rail.element_handle())

        outline_button.click()
        expect(page.get_by_role("heading", name="Outline")).to_be_visible()
        expect(page.get_by_role("heading", name="Git Sync")).not_to_be_visible()
        page.wait_for_function(RAIL_OPEN_CHECK, arg=rail.element_handle())

        paddings = page.evaluate(
            """titles => titles.map(title => {
                const el = Array.from(document.querySelectorAll('button[title]'))
                    .find(node => node.title === title);
                if (!el) throw new Error(`Missing outline row: ${title}`);
                return getComputedStyle(el).paddingLeft;
            })""",
            ["Root", "Child", "Grandchild"],
        )
        assert len(set(paddings)) > 1, f"outline indentation collapsed: {paddings}"

        page.get_by_title("Copy note markdown").click()
        page.wait_for_function(
            "navigator.clipboard.readText().then(text => text.includes('Body for copy checks.'))"
        )
        copied_note = page.evaluate("navigator.clipboard.readText()")
        assert copied_note.rstrip() == NOTE_CONTENT.rstrip(), (
            "copied note markdown mismatch:\n"
            f"expected={NOTE_CONTENT!r}\n"
            f"actual={copied_note!r}"
        )

        page.locator(".toast-viewer").click(position={"x": 20, "y": 20})
        expect(page.get_by_role("heading", name="Outline")).not_to_be_visible()
        page.wait_for_function(RAIL_CLOSED_CHECK, arg=rail.element_handle())

        page.get_by_title("Copy Source").click()
        page.wait_for_function(
            "navigator.clipboard.readText().then(text => text.includes('graph TD'))"
        )
        copied_mermaid = page.evaluate("navigator.clipboard.readText()")
        assert "graph TD" in copied_mermaid
        assert "A[Start] --> B[Done]" in copied_mermaid

        browser.close()
        print("e2e passed")
        print(f"right tool rail transform: {open_transform}")
        print(f"outline paddings: {paddings}")


def main():
    require_command("pipenv")
    require_command("npm")
    require_command("git")
    write_seed_note()

    backend = ManagedProcess(
        "backend",
        [
            "pipenv",
            "run",
            "python",
            "-m",
            "uvicorn",
            "main:app",
            "--app-dir",
            "server",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        env=backend_env(),
    )
    frontend = ManagedProcess(
        "frontend",
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "8080"],
    )

    processes = [backend, frontend]
    try:
        for process in processes:
            process.start()
        wait_for_url(f"{API_URL}/health")
        wait_for_url(BASE_URL)
        run_browser_checks()
    finally:
        for process in reversed(processes):
            process.stop()


if __name__ == "__main__":
    main()
