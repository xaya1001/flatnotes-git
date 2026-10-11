import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { defineComponent } from "vue";
import { renderMermaidBlocks } from "../../../client/components/toastui/mermaidRenderer.js";

// --- Mock the actual InteractiveMermaid component ---
//
// THE KEY FIX IS HERE: The mocked component's template MUST NOT have the
// same class name as the wrapper div we search for in the tests.
// The real component has this class on its root, but for the isolated test,
// this creates a nested structure that fools querySelectorAll.
//
vi.mock("../../../client/components/toastui/InteractiveMermaid.vue", () => ({
  default: defineComponent({
    name: "InteractiveMermaid",
    props: ["diagramText"],
    // We give it a unique, "internal" class name instead.
    template: `<div class="mocked-interactive-mermaid">Mocked: {{ diagramText }}</div>`,
  }),
}));

describe("mermaidRenderer function", () => {
  let container;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    container.innerHTML = "";
    document.body.removeChild(container);
    container = null;
    vi.clearAllMocks();
  });

  it("should find and replace a single mermaid block", async () => {
    container.innerHTML = `<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>`;
    await renderMermaidBlocks(container);

    // Assert that the wrapper div was created
    expect(
      container.querySelectorAll(".mermaid-component-wrapper"),
    ).toHaveLength(1);
    // Assert that the mocked component was mounted inside it
    expect(
      container.querySelector(".mocked-interactive-mermaid"),
    ).not.toBeNull();
    // Assert the original element is hidden
    expect(container.querySelector("pre.lang-mermaid").style.display).toBe(
      "none",
    );
  });

  it("should replace multiple mermaid blocks", async () => {
    container.innerHTML = `
      <pre class="lang-mermaid"><code>graph LR; X-->Y;</code></pre>
      <pre class="lang-mermaid"><code>sequenceDiagram; A->>B: Hello;</code></pre>
    `;
    await renderMermaidBlocks(container);
    expect(
      container.querySelectorAll(".mermaid-component-wrapper"),
    ).toHaveLength(2);
  });

  it("should correctly clean up and re-render on subsequent calls", async () => {
    container.innerHTML = `<pre class="lang-mermaid"><code>graph TD; C-->D;</code></pre>`;

    // First render
    await renderMermaidBlocks(container);
    expect(
      container.querySelectorAll(".mermaid-component-wrapper"),
    ).toHaveLength(1);

    // Modify the DOM and re-render
    container.innerHTML += `<pre class="lang-mermaid"><code>graph TD; E-->F;</code></pre>`;
    await renderMermaidBlocks(container);

    // The atomic nature of renderMermaidBlocks should result in exactly 2 wrappers.
    expect(
      container.querySelectorAll(".mermaid-component-wrapper"),
    ).toHaveLength(2);
  });

  it("should ignore empty or whitespace-only mermaid blocks", async () => {
    container.innerHTML = `<pre class="lang-mermaid"><code>    </code></pre>`;
    await renderMermaidBlocks(container);
    expect(
      container.querySelectorAll(".mermaid-component-wrapper"),
    ).toHaveLength(0);
  });

  it("should handle a mix of valid and empty blocks", async () => {
    container.innerHTML = `
      <pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>
      <pre class="lang-mermaid"><code></code></pre>
      <pre class="lang-mermaid"><code>graph TD; C-->D;</code></pre>
    `;
    await renderMermaidBlocks(container);
    expect(
      container.querySelectorAll(".mermaid-component-wrapper"),
    ).toHaveLength(2);
  });
});
