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

// At the top of mermaidRenderer.spec.js, after other imports
import { usePanAndZoom } from '../composables/usePanAndZoom.js';
import { ref } from 'vue';

// Mock usePanAndZoom
vi.mock('../composables/usePanAndZoom.js', () => {
  const actualUsePanAndZoom = vi.importActual('../composables/usePanAndZoom.js');
  return {
    ...actualUsePanAndZoom, // Import and retain actual functionalities if needed for some tests
    usePanAndZoom: vi.fn(() => ({ // Mock the composable itself
      zoomIn: vi.fn(),
      zoomOut: vi.fn(),
      reset: vi.fn(),
      onMouseDown: vi.fn(),
      onMouseMove: vi.fn(),
      onMouseUp: vi.fn(),
      onWheel: vi.fn(),
      scale: ref(1),
      panX: ref(0),
      panY: ref(0),
      isPanning: ref(false),
    })),
  };
});

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
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    const diagramText = "graph TD; A-->B;";
    container.innerHTML = `<pre class="lang-mermaid"><code>${diagramText}</code></pre>`;
    await renderMermaidBlocks(container);
    expect(mermaid.render).toHaveBeenCalledOnce();
    const svgContainer = container.querySelector("div[data-mermaid-svg-id]");
    expect(svgContainer.textContent).toBe(diagramText);
  });

  it("should render multiple mermaid blocks correctly", async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
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
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = `<pre class="lang-mermaid"><code>graph TD; C-->D;</code></pre>`;
    await renderMermaidBlocks(container);
    await renderMermaidBlocks(container);
    expect(container.querySelectorAll("div[data-mermaid-svg-id]")).toHaveLength(
      1,
    );
    expect(mermaid.render).toHaveBeenCalledTimes(2);
  });

  it("should handle rendering errors gracefully", async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
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
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = `<pre class="lang-mermaid"><code>    </code></pre>`;
    await renderMermaidBlocks(container);
    expect(mermaid.render).not.toHaveBeenCalled();
  });

  describe("Theme Initialization and Switching", () => {
    it("should initialize with strict security level on first import", async () => {
      await import("../mermaidRenderer.js");
      const mockedMermaid = (await import("mermaid")).default;
      expect(mockedMermaid.initialize).toHaveBeenCalledWith({
        startOnLoad: false,
        securityLevel: "strict",
      });
    });

    it("should call reinitializeMermaidTheme with the correct theme", async () => {
      const { reinitializeMermaidTheme } = await import(
        "../mermaidRenderer.js"
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

// ... (existing describe and test blocks) ...

describe('Mermaid Renderer - Pan and Zoom Functionality', () => {
  let container;
  let mockPanZoomInstance;

  beforeEach(async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    // Reset mocks and get the new mock instance for each test
    vi.clearAllMocks();

    // Re-import to get fresh mocks if mermaid.initialize is relevant per test
    const mermaidMock = (await import("mermaid")).default;
    mermaidMock.initialize.mockClear();
    mermaidMock.render.mockClear().mockImplementation((id, text) => {
        return Promise.resolve({
            svg: `<svg id="${id}" class="mock-mermaid-svg">${text}</svg>`,
            bindFunctions: vi.fn(),
        });
    });

    // Get the mocked instance of usePanAndZoom's return value
    // This requires usePanAndZoom to have been called by renderMermaidBlocks
    // We can also set up a spy on the usePanAndZoom import itself.
    // For simplicity, we'll check for calls on the functions it returns.
    mockPanZoomInstance = usePanAndZoom(); // Call to get the mocked functions object
  });

  afterEach(() => {
    document.body.removeChild(container);
    container = null;
    vi.clearAllMocks();
  });

  it('should create pan and zoom controls for a rendered mermaid diagram', async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = '<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>';
    await renderMermaidBlocks(container);

    const panZoomContainer = container.querySelector('.mermaid-pan-zoom-container');
    expect(panZoomContainer).not.toBeNull();

    const controlsPanel = panZoomContainer.querySelector('.mermaid-controls-panel');
    expect(controlsPanel).not.toBeNull();
    expect(controlsPanel.style.display).toBe('none'); // Initially hidden

    const zoomInButton = controlsPanel.querySelector('button:nth-child(1)');
    const zoomOutButton = controlsPanel.querySelector('button:nth-child(2)');
    const resetButton = controlsPanel.querySelector('button:nth-child(3)');

    expect(zoomInButton).not.toBeNull();
    expect(zoomInButton.textContent).toBe('+');
    expect(zoomOutButton).not.toBeNull();
    expect(zoomOutButton.textContent).toBe('-');
    expect(resetButton).not.toBeNull();
    expect(resetButton.textContent).toBe('Reset');
  });

  it('should show controls on mouseenter and hide on mouseleave', async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = '<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>';
    await renderMermaidBlocks(container);

    const panZoomContainer = container.querySelector('.mermaid-pan-zoom-container');
    const controlsPanel = panZoomContainer.querySelector('.mermaid-controls-panel');

    panZoomContainer.dispatchEvent(new MouseEvent('mouseenter'));
    expect(controlsPanel.style.display).toBe('flex');

    panZoomContainer.dispatchEvent(new MouseEvent('mouseleave'));
    expect(controlsPanel.style.display).toBe('none');
  });

  it('should call zoomIn when zoomInButton is clicked', async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = '<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>';
    await renderMermaidBlocks(container);

    // At this point, renderMermaidBlocks has called usePanAndZoom.
    // We need to get the mock functions that were returned by that specific call.
    // The mock setup ensures usePanAndZoom always returns the same set of mock functions.
    const { zoomIn } = usePanAndZoom(); // Get the mocked functions

    const zoomInButton = container.querySelector('.mermaid-controls-panel button:nth-child(1)');
    zoomInButton.click();
    expect(zoomIn).toHaveBeenCalledTimes(1);
  });

  it('should call zoomOut when zoomOutButton is clicked', async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = '<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>';
    await renderMermaidBlocks(container);
    const { zoomOut } = usePanAndZoom(); // Get the mocked functions

    const zoomOutButton = container.querySelector('.mermaid-controls-panel button:nth-child(2)');
    zoomOutButton.click();
    expect(zoomOut).toHaveBeenCalledTimes(1);
  });

  it('should call reset when resetButton is clicked', async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = '<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>';
    await renderMermaidBlocks(container);
    const { reset } = usePanAndZoom(); // Get the mocked functions

    const resetButton = container.querySelector('.mermaid-controls-panel button:nth-child(3)');
    resetButton.click();
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it('should attach mousedown and wheel listeners to panZoomContainer', async () => {
    const { renderMermaidBlocks } = await import("../mermaidRenderer.js");
    container.innerHTML = '<pre class="lang-mermaid"><code>graph TD; A-->B;</code></pre>';

    // Spy on addEventListener for panZoomContainer
    // This is tricky because panZoomContainer is created inside renderMermaidBlocks
    // Instead, we rely on the fact that usePanAndZoom's onMouseDown and onWheel are called
    // by the event listeners set up in mermaidRenderer.js
    const { onMouseDown, onWheel } = usePanAndZoom();

    await renderMermaidBlocks(container);
    const panZoomContainer = container.querySelector('.mermaid-pan-zoom-container');

    panZoomContainer.dispatchEvent(new MouseEvent('mousedown', { button: 0 }));
    expect(onMouseDown).toHaveBeenCalled();

    panZoomContainer.dispatchEvent(new WheelEvent('wheel', { deltaY: 100 }));
    expect(onWheel).toHaveBeenCalled();
  });
});
