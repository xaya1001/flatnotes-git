// client/git-integration/tests/InteractiveMermaid.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import mermaid from "mermaid";
import InteractiveMermaid from "../../components/toastui/InteractiveMermaid.vue";

// --- Mock Setup ---
// Mock the entire Mermaid module
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(),
  },
}));

// Mock the Clipboard API globally
Object.assign(navigator, {
  clipboard: {
    // Ensure the mock for writeText is defined and returns a Promise
    writeText: vi.fn(),
  },
});

describe("InteractiveMermaid.vue", () => {
  let wrapper;

  // Helper to mount the component
  const mountComponent = (props = {}) => {
    return mount(InteractiveMermaid, {
      props: {
        diagramText: "graph TD; A-->B;",
        ...props,
      },
    });
  };

  // Setup mocks before each test
  beforeEach(() => {
    // Provide a fresh mock implementation for mermaid.render
    vi.mocked(mermaid.render).mockResolvedValue({
      svg: `<svg class="mermaid-svg">mocked svg</svg>`,
      bindFunctions: vi.fn(),
    });
    // FIX: Ensure navigator.clipboard.writeText returns a Promise to prevent '.then' of undefined error
    vi.mocked(navigator.clipboard.writeText).mockResolvedValue(undefined);
  });

  // Cleanup after each test
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    // Clears all mock history and restores original implementations if they were spied on
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("renders the Mermaid SVG when mounted", async () => {
      wrapper = mountComponent();
      // flushPromises will wait for all pending async operations to complete
      await flushPromises();

      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.exists()).toBe(true);
      expect(mermaid.render).toHaveBeenCalledOnce();
    });

    it("displays an error message if Mermaid rendering fails", async () => {
      vi.mocked(mermaid.render).mockRejectedValue(new Error("Syntax error"));

      wrapper = mountComponent();
      await flushPromises();

      const errorBox = wrapper.find(".mermaid-error-box");
      expect(errorBox.exists()).toBe(true);
      expect(errorBox.text()).toContain("Syntax error");

      // No need to restore spy here, afterEach with vi.restoreAllMocks() handles it.
    });

    it("re-renders when the diagramText prop changes", async () => {
      wrapper = mountComponent();
      await flushPromises();

      // Clear call history from the initial render
      vi.mocked(mermaid.render).mockClear();

      // Setup a new mock return value for the re-render
      vi.mocked(mermaid.render).mockResolvedValue({
        svg: `<svg class="mermaid-svg">new graph</svg>`,
        bindFunctions: vi.fn(),
      });

      await wrapper.setProps({ diagramText: "graph LR; C-->D;" });
      await flushPromises();

      expect(mermaid.render).toHaveBeenCalledOnce();
      expect(wrapper.find("svg.mermaid-svg").text()).toBe("new graph");
    });
  });

  describe("UI Interaction", () => {
    beforeEach(async () => {
      wrapper = mountComponent();
      await flushPromises();
    });

    it("copies the diagram source to the clipboard", async () => {
      await wrapper.find('button[title="Copy Source"]').trigger("click");

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "graph TD; A-->B;",
      );
    });

    it("zooms in on button click", async () => {
      const initialScale = wrapper.vm.scale;
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      expect(wrapper.vm.scale).toBeGreaterThan(initialScale);
    });

    it("zooms out on button click", async () => {
      const initialScale = wrapper.vm.scale;
      await wrapper.find('button[title="Zoom Out"]').trigger("click");
      expect(wrapper.vm.scale).toBeLessThan(initialScale);
    });

    it("resets view on button click", async () => {
      wrapper.vm.scale = 2.0; // Manually change state
      await wrapper.find('button[title="Reset View"]').trigger("click");
      expect(wrapper.vm.scale).toBe(1);
    });

    it("toggles fullscreen mode on button click", async () => {
      expect(wrapper.vm.isFullscreen).toBe(false);
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      expect(wrapper.vm.isFullscreen).toBe(true);
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      expect(wrapper.vm.isFullscreen).toBe(false);
    });
  });

  describe("Theming", () => {
    it("initializes with 'default' theme for light mode", async () => {
      document.body.className = "";
      wrapper = mountComponent();
      await flushPromises();

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
    });

    it("initializes with 'dark' theme for dark mode", async () => {
      document.body.className = "dark";
      wrapper = mountComponent();
      await flushPromises();

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({ theme: "dark" }),
      );
    });
  });
});
