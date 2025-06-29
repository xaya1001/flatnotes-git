// client/git-integration/tests/mermaidRenderer.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import mermaid from "mermaid";

// --- MOCKING AREA ---

vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockImplementation((id, text) => {
      return Promise.resolve({
        svg: `<svg id="${id}" class="mock-mermaid-svg">${text}</svg>`,
        bindFunctions: vi.fn(),
      });
    }),
  },
}));

vi.mock("uuid", () => ({
  v4: vi.fn(() => "test-uuid"),
}));

// --- END MOCKING AREA ---

describe("mermaidRenderer.js", () => {
  let container;
  let consoleErrorSpy;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.clearAllMocks();
  });

  afterEach(() => {
    document.body.removeChild(container);
    container = null;
    consoleErrorSpy.mockRestore();
    vi.resetModules();
  });

  it("should find and render a single mermaid block", async () => {
    const { renderMermaidBlocks } = await import(
      "../../components/toastui/mermaidRenderer.js"
    );
    const diagramText = "graph TD; A-->B;";
    container.innerHTML = `<pre class="lang-mermaid"><code>${diagramText}</code></pre>`;
    await renderMermaidBlocks(container);
    expect(mermaid.render).toHaveBeenCalledOnce();
    const svgContainer = container.querySelector("div[data-mermaid-svg-id]");
    expect(svgContainer.textContent).toBe(diagramText);
  });

  it("should render multiple mermaid blocks correctly", async () => {
    const { renderMermaidBlocks } = await import(
      "../../components/toastui/mermaidRenderer.js"
    );
    container.innerHTML = `
      <pre class="lang-mermaid"><code>graph LR; X-->Y;</code></pre>
      <pre class="lang-mermaid"><code>sequenceDiagram; A->>B: Hello;</code></pre>
    `;
    await renderMermaidBlocks(container);
    const svgContainers = container.querySelectorAll(
      "div[data-mermaid-svg-id]",
    );
    expect(svgContainers[0].textContent).toBe("graph LR; X-->Y;");
    expect(svgContainers[1].textContent).toBe("sequenceDiagram; A->>B: Hello;");
  });

  it("should clean up old SVGs and errors before re-rendering", async () => {
    const { renderMermaidBlocks } = await import(
      "../../components/toastui/mermaidRenderer.js"
    );
    container.innerHTML = `<pre class="lang-mermaid"><code>graph TD; C-->D;</code></pre>`;
    await renderMermaidBlocks(container);
    await renderMermaidBlocks(container);
    expect(container.querySelectorAll("div[data-mermaid-svg-id]")).toHaveLength(
      1,
    );
    expect(mermaid.render).toHaveBeenCalledTimes(2);
  });

  it("should handle rendering errors gracefully", async () => {
    const { renderMermaidBlocks } = await import(
      "../../components/toastui/mermaidRenderer.js"
    );
    const errorMessage = "Mermaid syntax error!";
    mermaid.render.mockRejectedValue(new Error(errorMessage));
    container.innerHTML = `<pre class="lang-mermaid"><code>invalid diagram</code></pre>`;

    await renderMermaidBlocks(container);

    // Assert that the original pre element is now hidden
    const preElement = container.querySelector("pre.lang-mermaid");
    expect(preElement.style.display).toBe("none");

    // Assert that a new error container was created and inserted
    const errorContainer = container.querySelector("div[data-mermaid-error]");
    expect(errorContainer).not.toBeNull();

    // Assert that the error container has the correct message
    expect(errorContainer.textContent).toContain(
      "Error rendering Mermaid diagram",
    );
    expect(errorContainer.textContent).toContain(errorMessage);

    // Assert the error was logged
    expect(consoleErrorSpy).toHaveBeenCalled();
  });

  it("should ignore empty or whitespace-only mermaid blocks", async () => {
    const { renderMermaidBlocks } = await import(
      "../../components/toastui/mermaidRenderer.js"
    );
    container.innerHTML = `<pre class="lang-mermaid"><code>    </code></pre>`;
    await renderMermaidBlocks(container);
    expect(mermaid.render).not.toHaveBeenCalled();
  });

  describe("Theme Initialization and Switching", () => {
    it("should initialize with strict security level on first import", async () => {
      await import("../../components/toastui/mermaidRenderer.js");
      const mockedMermaid = (await import("mermaid")).default;
      expect(mockedMermaid.initialize).toHaveBeenCalledWith({
        startOnLoad: false,
        securityLevel: "strict",
      });
    });

    it("should call reinitializeMermaidTheme with the correct theme", async () => {
      const { reinitializeMermaidTheme } = await import(
        "../../components/toastui/mermaidRenderer.js"
      );
      const mockedMermaid = (await import("mermaid")).default;
      mockedMermaid.initialize.mockClear();

      reinitializeMermaidTheme("dark");
      expect(mockedMermaid.initialize).toHaveBeenCalledWith({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "dark",
      });

      reinitializeMermaidTheme("default");
      expect(mockedMermaid.initialize).toHaveBeenCalledWith({
        startOnLoad: false,
        securityLevel: "strict",
        theme: "default",
      });
    });
  });
});
