// client/git-integration/tests/InteractiveMermaid.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import mermaid from "mermaid";
import InteractiveMermaid from "../../components/toastui/InteractiveMermaid.vue";

// Mock the entire Mermaid module
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(),
  },
}));

// Mock the Clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

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
    // Provide a fresh, reliable mock implementation before each test
    vi.mocked(mermaid.render).mockResolvedValue({
      svg: `<svg class="mermaid-svg">mocked svg</svg>`,
      bindFunctions: vi.fn(),
    });
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    // Restore all mocks to ensure test isolation
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("renders the Mermaid SVG when mounted", async () => {
      wrapper = mountComponent();
      await nextTick(); // onMounted
      await nextTick(); // async render

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
      await nextTick();
      await nextTick();

      const errorBox = wrapper.find(".mermaid-error-box");
      expect(errorBox.exists()).toBe(true);
      expect(errorBox.text()).toContain("Syntax error");

      consoleErrorSpy.mockRestore();
    });

    it("re-renders when the diagramText prop changes", async () => {
      wrapper = mountComponent();
      await nextTick();
      await nextTick();

      vi.clearAllMocks();
      vi.mocked(mermaid.render).mockResolvedValue({
        svg: `<svg class="mermaid-svg">new graph</svg>`,
        bindFunctions: vi.fn(),
      });

      await wrapper.setProps({ diagramText: "graph LR; C-->D;" });
      await nextTick();
      await nextTick();

      expect(mermaid.render).toHaveBeenCalledOnce();
      expect(wrapper.find("svg.mermaid-svg").text()).toBe("new graph");
    });
  });

  describe("User Interaction", () => {
    beforeEach(async () => {
      wrapper = mountComponent();
      await nextTick();
      await nextTick();
    });

    it("copies the diagram source to the clipboard", async () => {
      // Use .stop modifier on button to prevent mousedown from propagating
      await wrapper.find('button[title="Copy Source"]').trigger("click");
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "graph TD; A-->B;",
      );
    });

    it("zooms in on button click", async () => {
      const initialScale = wrapper.vm.scale;
      await wrapper.find('button[title="Zoom In"]').trigger("click.stop");
      expect(wrapper.vm.scale).toBeGreaterThan(initialScale);
    });

    it("zooms out on button click", async () => {
      const initialScale = wrapper.vm.scale;
      await wrapper.find('button[title="Zoom Out"]').trigger("click.stop");
      expect(wrapper.vm.scale).toBeLessThan(initialScale);
    });

    it("resets view on button click", async () => {
      wrapper.vm.scale = 2.0;
      await nextTick();
      await wrapper.find('button[title="Reset View"]').trigger("click.stop");
      expect(wrapper.vm.scale).toBe(1);
    });
  });

  describe("Theming", () => {
    it("initializes with 'default' theme for light mode", async () => {
      document.body.className = "";
      wrapper = mountComponent();
      await nextTick();

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({ theme: "default" }),
      );
    });

    it("initializes with 'dark' theme for dark mode", async () => {
      document.body.className = "dark";
      wrapper = mountComponent();
      await nextTick();

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({ theme: "dark" }),
      );
    });
  });
});
