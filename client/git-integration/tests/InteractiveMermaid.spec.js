// client/git-integration/tests/InteractiveMermaid.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import mermaid from "mermaid";
import InteractiveMermaid from "../../components/toastui/InteractiveMermaid.vue";

// --- Mocking Area ---
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockImplementation((id, text, container) => {
      if (container) {
        container.innerHTML = `<svg id="${id}" class="mermaid-svg">${text}</svg>`;
      }
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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
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
        expect.any(HTMLElement),
      );

      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.exists()).toBe(true);
      expect(svgElement.text()).toBe("graph TD; A-->B;");
    });

    it("displays an error message if Mermaid rendering fails", async () => {
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const errorMessage = "Invalid syntax";
      mermaid.render.mockRejectedValueOnce(new Error(errorMessage));

      wrapper = mountComponent();
      await wrapper.vm.$nextTick();

      const errorBox = wrapper.find("pre.mermaid-error-text");
      expect(errorBox.exists()).toBe(true);
      expect(errorBox.text()).toContain(errorMessage);

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
        expect.any(HTMLElement),
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
      // Simulate zooming in first
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      expect(wrapper.vm.scale).not.toBe(1);

      // Now reset
      await wrapper.find('button[title="Reset View"]').trigger("click");

      // FIX: Only check the scale property, as panX and panY are removed.
      expect(wrapper.vm.scale).toBe(1);
    });

    it("zooms with ctrl/meta key + wheel, but not without", async () => {
      const initialScale = wrapper.vm.scale;
      // FIX: Find the correct element that listens to the wheel event.
      const scrollWrapper = wrapper.find(".mermaid-scroll-wrapper");
      const containerElement = scrollWrapper.element;

      const normalWheelEvent = new WheelEvent("wheel", {
        bubbles: true,
        deltaY: -50,
        ctrlKey: false,
      });
      containerElement.dispatchEvent(normalWheelEvent);
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scale).toBe(initialScale); // Should not zoom

      const ctrlWheelEvent = new WheelEvent("wheel", {
        bubbles: true,
        deltaY: -50,
        ctrlKey: true,
      });
      containerElement.dispatchEvent(ctrlWheelEvent);
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scale).toBeGreaterThan(initialScale); // Should zoom
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
      const wrapper = mountComponent();
      await wrapper.vm.$nextTick();

      expect(mermaid.initialize).toHaveBeenCalledTimes(1);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(1);

      document.body.classList.add("dark");
      await wrapper.vm.$nextTick();

      expect(mermaid.initialize).toHaveBeenCalledTimes(2);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "dark" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(2);

      document.body.classList.remove("dark");
      await wrapper.vm.$nextTick();

      expect(mermaid.initialize).toHaveBeenCalledTimes(3);
      expect(mermaid.initialize).toHaveBeenLastCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
      expect(mermaid.render).toHaveBeenCalledTimes(3);
    });
  });
});
