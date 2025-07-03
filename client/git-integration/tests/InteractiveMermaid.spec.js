// client/git-integration/tests/InteractiveMermaid.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import mermaid from "mermaid";
import InteractiveMermaid from "../../components/toastui/InteractiveMermaid.vue";

// --- Mock Setup ---
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(),
  },
}));

Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(),
  },
});

describe("InteractiveMermaid.vue", () => {
  let wrapper;

  const mountComponent = (props = {}) => {
    // Attach to the document's body so the MutationObserver can see it
    return mount(InteractiveMermaid, {
      attachTo: document.body,
      props: {
        diagramText: "graph TD; A-->B;",
        ...props,
      },
    });
  };

  beforeEach(() => {
    document.body.className = ""; // Reset body class
    vi.mocked(mermaid.render).mockResolvedValue({
      svg: `<svg class="mermaid-svg">mocked svg</svg>`,
      bindFunctions: vi.fn(),
    });
    vi.mocked(navigator.clipboard.writeText).mockResolvedValue(undefined);
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("renders the Mermaid SVG when mounted", async () => {
      wrapper = mountComponent();
      await flushPromises();

      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.exists()).toBe(true);
      expect(mermaid.render).toHaveBeenCalledOnce();
    });

    it("displays an error message if Mermaid rendering fails", async () => {
      vi.mocked(mermaid.render).mockRejectedValue(new Error("Syntax error"));
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      wrapper = mountComponent();
      await flushPromises();

      const errorBox = wrapper.find(".mermaid-error-box");
      expect(errorBox.exists()).toBe(true);
      expect(errorBox.text()).toContain("Syntax error");
    });

    it("re-renders when the diagramText prop changes", async () => {
      wrapper = mountComponent();
      await flushPromises();
      vi.mocked(mermaid.render).mockClear();
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
      wrapper.vm.scale = 2.0;
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

    // RESTORED AND IMPROVED TEST CASE
    it("re-initializes and re-renders when the body class changes", async () => {
      // 1. Initial state (light mode)
      document.body.className = "";
      wrapper = mountComponent();
      await flushPromises();

      // Assert initial call
      expect(mermaid.initialize).toHaveBeenCalledTimes(1);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
      // The render call happens after initialize
      expect(mermaid.render).toHaveBeenCalledTimes(1);

      // 2. Act: Change the DOM, simulating a theme toggle
      document.body.className = "dark";
      await flushPromises(); // Wait for MutationObserver and re-render

      // 3. Assert: Check for re-initialization and re-render with the new theme
      expect(mermaid.initialize).toHaveBeenCalledTimes(2);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "dark" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(2);

      // 4. Act: Change it back to light mode
      document.body.className = "";
      await flushPromises();

      // 5. Assert: Check again
      expect(mermaid.initialize).toHaveBeenCalledTimes(3);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(3);
    });
  });
});
