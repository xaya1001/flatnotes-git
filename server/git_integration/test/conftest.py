# server/git_integration/test/conftest.py (FINAL VERSION)

import os
import subprocess

import pygit2
import pytest

from ..git_config import PullStrategy
from ..git_manager import GitManager

# --- Centralized Test Configuration ---
TEST_USER_NAME = "Test User"
TEST_USER_EMAIL = "test@example.com"
TEST_BRANCH_MAIN = "main"

# --- Shared Fixtures ---


@pytest.fixture
def run_git():
    """Provides the git command execution function as a fixture."""

    def _run_git_subprocess(repo_path, command):
        return subprocess.run(
            ["git"] + command,
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    return _run_git_subprocess


@pytest.fixture
def base_repo_path(tmp_path, run_git):
    """Creates a basic, initialized git repository path."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    run_git(repo_path, ["init", f"--initial-branch={TEST_BRANCH_MAIN}"])
    run_git(repo_path, ["config", "user.name", TEST_USER_NAME])
    run_git(repo_path, ["config", "user.email", TEST_USER_EMAIL])
    return str(repo_path)


@pytest.fixture
def manager_local(base_repo_path, run_git):
    """Provides a GitManager for a local-only repository."""
    run_git(base_repo_path, ["commit", "--allow-empty", "-m", "Initial empty commit"])
    manager = GitManager(
        repo_path=base_repo_path,
        default_branch=TEST_BRANCH_MAIN,
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name=TEST_USER_NAME,
        user_email=TEST_USER_EMAIL,
    )
    repo = pygit2.Repository(base_repo_path)
    return manager, repo, base_repo_path


@pytest.fixture
def manager_with_remote(base_repo_path, run_git):
    """Provides a GitManager for a repository connected to a remote."""
    local_path = base_repo_path
    remote_repo_dir = os.path.join(os.path.dirname(local_path), "remote_dir")
    os.makedirs(remote_repo_dir, exist_ok=True)
    remote_path = os.path.join(remote_repo_dir, "remote.git")

    run_git(
        remote_repo_dir,
        ["init", "--bare", f"--initial-branch={TEST_BRANCH_MAIN}", remote_path],
    )
    run_git(local_path, ["remote", "add", "origin", remote_path])
    with open(os.path.join(local_path, "README.md"), "w") as f:
        f.write("# Test Repository\n")
    run_git(local_path, ["add", "README.md"])
    run_git(local_path, ["commit", "-m", "Initial commit"])
    run_git(local_path, ["push", "-u", "origin", TEST_BRANCH_MAIN])

    manager = GitManager(
        repo_path=local_path,
        default_branch=TEST_BRANCH_MAIN,
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name=TEST_USER_NAME,
        user_email=TEST_USER_EMAIL,
    )
    repo = pygit2.Repository(local_path)
    yield manager, repo, local_path, remote_path
