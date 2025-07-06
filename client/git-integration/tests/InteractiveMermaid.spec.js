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

// Mock for focus restoration test
HTMLElement.prototype.focus = vi.fn();

describe("InteractiveMermaid.vue", () => {
  let wrapper;

  const mountComponent = (props = {}) => {
    return mount(InteractiveMermaid, {
      attachTo: document.body,
      props: {
        diagramText: "graph TD; A-->B;",
        ...props,
      },
    });
  };

  beforeEach(() => {
    document.body.className = "";
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
    HTMLElement.prototype.focus.mockClear();
  });

  describe("Rendering", () => {
    it("renders the Mermaid SVG when mounted", async () => {
      wrapper = mountComponent();
      await flushPromises();
      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.exists()).toBe(true);
      expect(mermaid.render).toHaveBeenCalledOnce();
    });

    // NEW TEST: Test empty state
    it("displays an empty state message when diagramText is empty", async () => {
      wrapper = mountComponent({ diagramText: "  " }); // Whitespace only
      await flushPromises();
      expect(wrapper.find(".mermaid-empty-state").exists()).toBe(true);
      expect(wrapper.find(".mermaid-empty-state").text()).toBe(
        "No diagram to display",
      );
      expect(mermaid.render).not.toHaveBeenCalled();
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
      const initialScale = wrapper.vm.transform.scale;
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      expect(wrapper.vm.transform.scale).toBeGreaterThan(initialScale);
    });

    it("zooms out on button click", async () => {
      const initialScale = wrapper.vm.transform.scale;
      await wrapper.find('button[title="Zoom Out"]').trigger("click");
      expect(wrapper.vm.transform.scale).toBeLessThan(initialScale);
    });

    it("resets view on button click", async () => {
      wrapper.vm.transform.scale = 2.0;
      await wrapper.find('button[title="Reset View"]').trigger("click");
      expect(wrapper.vm.transform.scale).toBe(1);
    });
  });

  // NEW TEST SUITE: Fullscreen mode deep testing
  describe("Fullscreen Mode", () => {
    let containerEl;

    beforeEach(async () => {
      wrapper = mountComponent();
      await flushPromises();
      containerEl = wrapper.find(".mermaid-diagram-container").element;
    });

    it("adds and removes event listeners when toggling fullscreen", async () => {
      const addSpy = vi.spyOn(containerEl, "addEventListener");
      const removeSpy = vi.spyOn(containerEl, "removeEventListener");

      // Enter fullscreen
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();

      expect(addSpy).toHaveBeenCalledWith("mousedown", expect.any(Function));
      expect(addSpy).toHaveBeenCalledWith("wheel", expect.any(Function));
      addSpy.mockClear();

      // Exit fullscreen
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();

      expect(removeSpy).toHaveBeenCalledWith("mousedown", expect.any(Function));
      expect(removeSpy).toHaveBeenCalledWith("wheel", expect.any(Function));
    });

    it("exits fullscreen on Escape key press", async () => {
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      expect(wrapper.vm.isFullscreen).toBe(true);

      // Simulate Escape key press on the window
      const event = new KeyboardEvent("keydown", { key: "Escape" });
      window.dispatchEvent(event);
      await flushPromises();

      expect(wrapper.vm.isFullscreen).toBe(false);
    });

    it("restores focus to the trigger element after exiting fullscreen", async () => {
      const fullscreenButton = wrapper.find(
        'button[title="Toggle Fullscreen"]',
      ).element;

      // Enter fullscreen by clicking the button
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();

      // Exit fullscreen
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();

      // Check if focus was called on the original button
      expect(fullscreenButton.focus).toHaveBeenCalledOnce();
    });

    it("restores focus after exiting fullscreen with Escape key", async () => {
      const fullscreenButton = wrapper.find(
        'button[title="Toggle Fullscreen"]',
      ).element;

      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();

      const event = new KeyboardEvent("keydown", { key: "Escape" });
      window.dispatchEvent(event);
      await flushPromises();

      expect(fullscreenButton.focus).toHaveBeenCalledOnce();
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

    it("re-initializes and re-renders when the body class changes", async () => {
      document.body.className = "";
      wrapper = mountComponent();
      await flushPromises();
      expect(mermaid.render).toHaveBeenCalledTimes(1);

      document.body.className = "dark";
      await flushPromises();
      expect(mermaid.render).toHaveBeenCalledTimes(2);

      document.body.className = "";
      await flushPromises();
      expect(mermaid.render).toHaveBeenCalledTimes(3);
    });
  });
});
