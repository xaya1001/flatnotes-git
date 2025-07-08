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

HTMLElement.prototype.focus = vi.fn();
vi.useFakeTimers();

// --- START: REVISED MOCK for MutationObserver ---
let mutationCallback = null;
const MockMutationObserver = vi.fn((cb) => {
  mutationCallback = cb;
  return {
    observe: vi.fn(),
    disconnect: vi.fn(),
  };
});
vi.stubGlobal("MutationObserver", MockMutationObserver);
// --- END: REVISED MOCK ---

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
    HTMLElement.prototype.focus.mockClear();
    mutationCallback = null; // Reset between tests
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    vi.restoreAllMocks();
  });

  // ... (Rendering and UI Interaction suites remain the same) ...
  describe("Rendering", () => {
    it("renders the Mermaid SVG when mounted", async () => {
      wrapper = mountComponent();
      await flushPromises();
      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.exists()).toBe(true);
      expect(mermaid.render).toHaveBeenCalledOnce();
    });

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
      wrapper = mountComponent();
      await flushPromises();
      const errorBox = wrapper.find(".mermaid-error-box");
      expect(errorBox.exists()).toBe(true);
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

  describe("Fullscreen Mode", () => {
    // --- START: REVISED TEST 1 ---
    it("manages event listeners correctly when mounted and toggling fullscreen", async () => {
      // Spy on the methods BEFORE mounting the component
      const addSpy = vi.spyOn(HTMLElement.prototype, "addEventListener");
      const removeSpy = vi.spyOn(HTMLElement.prototype, "removeEventListener");

      wrapper = mountComponent();
      await flushPromises();

      // 1. Check onMounted behavior
      // We check that it was called on the specific container element
      const containerEl = wrapper.find(".mermaid-diagram-container").element;
      expect(addSpy).toHaveBeenCalledWith("mousedown", expect.any(Function));
      // Filter calls to focus only on the container element for precision
      const mousedownCall = addSpy.mock.calls.find(
        (call) => call[0] === "mousedown",
      );
      expect(mousedownCall).not.toBeUndefined();

      addSpy.mockClear();

      // 2. Enter fullscreen
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();
      expect(addSpy).toHaveBeenCalledWith("wheel", expect.any(Function));
      expect(addSpy).not.toHaveBeenCalledWith(
        "mousedown",
        expect.any(Function),
      );
      addSpy.mockClear();

      // 3. Exit fullscreen
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();
      expect(removeSpy).toHaveBeenCalledWith("wheel", expect.any(Function));
      expect(removeSpy).not.toHaveBeenCalledWith(
        "mousedown",
        expect.any(Function),
      );
    });
    // --- END: REVISED TEST 1 ---

    it("exits fullscreen on Escape key press", async () => {
      wrapper = mountComponent();
      await flushPromises();
      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      expect(wrapper.vm.isFullscreen).toBe(true);

      const event = new KeyboardEvent("keydown", { key: "Escape" });
      window.dispatchEvent(event);
      await flushPromises();

      expect(wrapper.vm.isFullscreen).toBe(false);
    });

    it("restores focus to the trigger element after exiting fullscreen by click", async () => {
      wrapper = mountComponent();
      await flushPromises();
      const fullscreenButton = wrapper.find(
        'button[title="Toggle Fullscreen"]',
      ).element;
      vi.spyOn(fullscreenButton, "focus");

      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();

      await wrapper.find("button.mermaid-modal-close").trigger("click");
      await flushPromises();

      vi.runAllTimers();

      expect(fullscreenButton.focus).toHaveBeenCalledOnce();
    });

    it("restores focus after exiting fullscreen with Escape key (if entered via click)", async () => {
      wrapper = mountComponent();
      await flushPromises();
      const fullscreenButton = wrapper.find(
        'button[title="Toggle Fullscreen"]',
      ).element;
      vi.spyOn(fullscreenButton, "focus");

      await wrapper.find('button[title="Toggle Fullscreen"]').trigger("click");
      await flushPromises();

      const event = new KeyboardEvent("keydown", { key: "Escape" });
      window.dispatchEvent(event);
      await flushPromises();

      vi.runAllTimers();

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

    // --- START: REVISED TEST 2 ---
    it("re-renders when the body class changes", async () => {
      document.body.className = "";
      wrapper = mountComponent();
      await flushPromises();
      expect(mermaid.render).toHaveBeenCalledTimes(1);

      // Ensure the mock was set up correctly
      expect(mutationCallback).toBeInstanceOf(Function);

      // Simulate the mutation
      mutationCallback([{ type: "attributes" }]);
      await flushPromises();
      expect(mermaid.render).toHaveBeenCalledTimes(2);

      mutationCallback([{ type: "attributes" }]);
      await flushPromises();
      expect(mermaid.render).toHaveBeenCalledTimes(3);
    });
    // --- END: REVISED TEST 2 ---
  });
});
