// client/git-integration/tests/mermaidRenderer.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderMermaidBlocks } from "../../components/toastui/mermaidRenderer.js";

// --- THIS IS THE PART TO CHANGE ---
// Mock the InteractiveMermaid component to accurately represent its root element.
vi.mock("../../components/toastui/InteractiveMermaid.vue", () => ({
  default: {
    name: "InteractiveMermaid",
    // The mock now has the real component's root class, so the cleanup step can find it.
    template:
      '<div class="mermaid-diagram-container"><div class="mock-internal-content"></div></div>',
    props: ["diagramText"],
  },
}));

describe("mermaidRenderer.js", () => {
  let container;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    vi.clearAllMocks();
  });

  afterEach(() => {
    document.body.removeChild(container);
    container = null;
  });

  // This test and the others will now pass without changes to their logic.
  it("should find and replace a single mermaid block with a component container", async () => {
    const diagramText = "graph TD; A-->B;";
    container.innerHTML = `<pre class="lang-mermaid"><code>${diagramText}</code></pre>`;

    await renderMermaidBlocks(container);

    const preElement = container.querySelector("pre.lang-mermaid");
    expect(preElement.style.display).toBe("none");

    // We now look for the class that the cleanup step uses.
    const componentContainer = container.querySelector(
      ".mermaid-diagram-container",
    );
    expect(componentContainer).not.toBeNull();
  });

  it("should replace multiple mermaid blocks", async () => {
    container.innerHTML = `
      <p>Some text</p>
      <pre class="lang-mermaid"><code>graph LR; X-->Y;</code></pre>
      <pre class="lang-mermaid"><code>sequenceDiagram; A->>B: Hello;</code></pre>
    `;

    await renderMermaidBlocks(container);

    const componentContainers = container.querySelectorAll(
      ".mermaid-diagram-container",
    );
    expect(componentContainers).toHaveLength(2);
  });

  // --- THIS TEST WILL NOW PASS ---
  it("should clean up old component containers before re-rendering", async () => {
    container.innerHTML = `<pre class="lang-mermaid"><code>graph TD; C-->D;</code></pre>`;

    // First render
    await renderMermaidBlocks(container);
    // We assert based on the class that is used for cleanup.
    expect(
      container.querySelectorAll(".mermaid-diagram-container"),
    ).toHaveLength(1);

    // Second render on the same container
    await renderMermaidBlocks(container);
    // The cleanup step should have removed the old one before adding the new one.
    expect(
      container.querySelectorAll(".mermaid-diagram-container"),
    ).toHaveLength(1);
  });

  it("should ignore empty or whitespace-only mermaid blocks", async () => {
    container.innerHTML = `<pre class="lang-mermaid"><code>    </code></pre>`;

    await renderMermaidBlocks(container);

    const componentContainer = container.querySelector(
      ".mermaid-diagram-container",
    );
    expect(componentContainer).toBeNull();
  });
});
