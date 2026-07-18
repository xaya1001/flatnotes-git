import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { enhanceCodeBlockCopy } from "../../../client/components/toastui/codeBlockCopy.js";

describe("code block copy enhancement", () => {
  let container;
  let writeText;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });
  });

  afterEach(() => {
    document.body.removeChild(container);
    container = null;
    vi.clearAllMocks();
  });

  it("adds a copy button to code blocks and copies code text", async () => {
    container.innerHTML = `<pre><code>const answer = 42;</code></pre>`;

    enhanceCodeBlockCopy(container);
    const button = container.querySelector(".toastui-code-copy-button");
    button.click();
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(button).not.toBeNull();
    expect(writeText).toHaveBeenCalledWith("const answer = 42;");
    expect(button.textContent).toBe("Copied");
  });

  it("does not add duplicate buttons when enhanced repeatedly", () => {
    container.innerHTML = `<pre><code>npm run build</code></pre>`;

    enhanceCodeBlockCopy(container);
    enhanceCodeBlockCopy(container);

    expect(
      container.querySelectorAll(".toastui-code-copy-button"),
    ).toHaveLength(1);
  });

  it("skips mermaid blocks", () => {
    container.innerHTML = `<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>`;

    enhanceCodeBlockCopy(container);

    expect(container.querySelector(".toastui-code-copy-button")).toBeNull();
  });
});
