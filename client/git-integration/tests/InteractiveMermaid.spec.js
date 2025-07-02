// client/git-integration/tests/InteractiveMermaid.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import mermaid from "mermaid";
import InteractiveMermaid from "../../components/toastui/InteractiveMermaid.vue";

// --- Mocking Area ---
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockImplementation((id, text) => {
      return Promise.resolve({
        svg: `<svg id="${id}" class="mermaid-svg">${text}</svg>`,
        bindFunctions: vi.fn(),
      });
    }),
  },
}));

Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});
// --- End Mocking Area ---

describe("InteractiveMermaid.vue", () => {
  let wrapper;

  const mountComponent = (props = {}) => {
    return mount(InteractiveMermaid, {
      props: {
        diagramText: "graph TD; A-->B;",
        ...props,
      },
    });
  };

  // This hook ensures each test starts with a clean slate.
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // This hook ensures each test cleans up after itself, preventing state leaks.
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    document.body.className = "";
  });

  // ADD THIS HOOK
  afterEach(() => {
    document.body.className = "";
  });

  describe("Rendering", () => {
    it("renders the Mermaid SVG when mounted", async () => {
      wrapper = mountComponent();
      await wrapper.vm.$nextTick();

      expect(mermaid.render).toHaveBeenCalledOnce();
      expect(mermaid.render).toHaveBeenCalledWith(
        expect.any(String),
        "graph TD; A-->B;",
      );

      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.exists()).toBe(true);
      expect(svgElement.text()).toBe("graph TD; A-->B;");
    });

    it("displays an error message if Mermaid rendering fails", async () => {
      // 1. Arrange: Spy on console.error and provide a mock implementation that does nothing.
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const errorMessage = "Invalid syntax";
      mermaid.render.mockRejectedValueOnce(new Error(errorMessage));

      wrapper = mountComponent();
      await wrapper.vm.$nextTick();

      // 2. Assert: The rest of the test remains the same.
      const errorBox = wrapper.find(".mermaid-error-box");
      expect(errorBox.exists()).toBe(true);
      expect(errorBox.text()).toContain("Error rendering Mermaid diagram");
      expect(errorBox.text()).toContain(errorMessage);

      // 3. Cleanup: Restore the original console.error implementation. This is VITAL for test isolation.
      consoleErrorSpy.mockRestore();
    });

    it("re-renders when the diagramText prop changes", async () => {
      wrapper = mountComponent();
      await wrapper.vm.$nextTick();
      expect(mermaid.render).toHaveBeenCalledTimes(1);

      await wrapper.setProps({ diagramText: "graph LR; C-->D;" });
      await wrapper.vm.$nextTick();

      expect(mermaid.render).toHaveBeenCalledTimes(2);
      expect(mermaid.render).toHaveBeenCalledWith(
        expect.any(String),
        "graph LR; C-->D;",
      );

      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.text()).toBe("graph LR; C-->D;");
    });
  });

  describe("User Interaction", () => {
    beforeEach(() => {
      wrapper = mountComponent();
    });

    it("copies the diagram source to the clipboard when copy button is clicked", async () => {
      const copyButton = wrapper.find('button[title="Copy Source"]');
      await copyButton.trigger("click");

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "graph TD; A-->B;",
      );
    });

    it("zooms in when zoom-in button is clicked", async () => {
      const initialScale = wrapper.vm.scale;
      const zoomInButton = wrapper.find('button[title="Zoom In"]');
      await zoomInButton.trigger("click");

      expect(wrapper.vm.scale).toBeGreaterThan(initialScale);
    });

    it("zooms out when zoom-out button is clicked", async () => {
      const initialScale = wrapper.vm.scale;
      const zoomOutButton = wrapper.find('button[title="Zoom Out"]');
      await zoomOutButton.trigger("click");

      expect(wrapper.vm.scale).toBeLessThan(initialScale);
    });

    it("resets view when reset button is clicked", async () => {
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      await wrapper
        .find(".mermaid-diagram-container")
        .trigger("mousedown", { clientX: 100, clientY: 100 });
      await wrapper
        .find(".mermaid-diagram-container")
        .trigger("mousemove", { clientX: 150, clientY: 150 });

      expect(wrapper.vm.scale).not.toBe(1);
      expect(wrapper.vm.panX).not.toBe(0);

      await wrapper.find('button[title="Reset View"]').trigger("click");

      expect(wrapper.vm.scale).toBe(1);
      expect(wrapper.vm.panX).toBe(0);
      expect(wrapper.vm.panY).toBe(0);
    });

    it("zooms with ctrl/meta key + wheel, but not without", async () => {
      const initialScale = wrapper.vm.scale;
      const containerElement = wrapper.find(
        ".mermaid-diagram-container",
      ).element;

      const normalWheelEvent = new WheelEvent("wheel", {
        bubbles: true,
        deltaY: -50,
        ctrlKey: false,
      });
      containerElement.dispatchEvent(normalWheelEvent);
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scale).toBe(initialScale);

      const ctrlWheelEvent = new WheelEvent("wheel", {
        bubbles: true,
        deltaY: -50,
        ctrlKey: true,
      });
      containerElement.dispatchEvent(ctrlWheelEvent);
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scale).toBeGreaterThan(initialScale);
    });
  });

  describe("Theming", () => {
    it("initializes with the default theme when body has no dark class", async () => {
      wrapper = mountComponent();
      await wrapper.vm.$nextTick();

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({
          theme: "default",
        }),
      );
    });

    it("initializes with the dark theme when body has a dark class", async () => {
      document.body.classList.add("dark");
      wrapper = mountComponent();
      await wrapper.vm.$nextTick();

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({
          theme: "dark",
        }),
      );
    });

    it("re-initializes and re-renders when the body class changes", async () => {
      // 1. Arrange: Mount the component.
      const wrapper = mountComponent();
      await wrapper.vm.$nextTick(); // Wait for initial render.

      // Initial state assertion
      expect(mermaid.initialize).toHaveBeenCalledTimes(1);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(1);

      // 2. Act: Simulate the theme change by modifying the DOM.
      document.body.classList.add("dark");
      await wrapper.vm.$nextTick(); // Wait for the MutationObserver and Vue to react.

      // 3. Assert: Verify the re-initialization and re-render with the new theme.
      expect(mermaid.initialize).toHaveBeenCalledTimes(2);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "dark" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(2);

      // 4. Act again: Revert the theme.
      document.body.classList.remove("dark");
      await wrapper.vm.$nextTick();

      // 5. Assert again: Verify it switches back correctly.
      expect(mermaid.initialize).toHaveBeenCalledTimes(3);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(3);
    });
  });
});
