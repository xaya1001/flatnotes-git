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

  // Helper function to mount the component
  const mountComponent = (props = {}) => {
    return mount(InteractiveMermaid, {
      props: {
        diagramText: "graph TD; A-->B;",
        ...props,
      },
    });
  };

  // Setup and teardown for each test
  beforeEach(() => {
    vi.clearAllMocks();

    // Provide a default reliable mock for mermaid.render before each test
    vi.mocked(mermaid.render).mockResolvedValue({
      svg: `<svg class="mermaid-svg">mocked svg</svg>`,
      bindFunctions: vi.fn(),
    });

    // Provide a default mock for getComputedStyle
    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      getPropertyValue: () => "",
    });
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
      await nextTick(); // Wait for onMounted and async operations
      await nextTick();

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

      vi.clearAllMocks(); // Clear mocks after initial render
      vi.mocked(mermaid.render).mockResolvedValue({
        svg: `<svg class="mermaid-svg">new graph</svg>`,
        bindFunctions: vi.fn(),
      });

      await wrapper.setProps({ diagramText: "graph LR; C-->D;" });
      await nextTick();
      await nextTick();

      expect(mermaid.render).toHaveBeenCalledOnce();
      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.text()).toBe("new graph");
    });
  });

  describe("User Interaction", () => {
    beforeEach(async () => {
      wrapper = mountComponent();
      await nextTick();
      await nextTick();
    });

    it("copies the diagram source to the clipboard", async () => {
      await wrapper.find('button[title="Copy Source"]').trigger("click");
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        "graph TD; A-->B;",
      );
    });

    it("zooms in on button click", async () => {
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      expect(wrapper.vm.scale).toBeGreaterThan(1);
    });

    it("zooms out on button click", async () => {
      await wrapper.find('button[title="Zoom Out"]').trigger("click");
      expect(wrapper.vm.scale).toBeLessThan(1);
    });

    it("resets view on button click", async () => {
      wrapper.vm.scale = 2.0;
      await nextTick();

      await wrapper.find('button[title="Reset View"]').trigger("click");
      expect(wrapper.vm.scale).toBe(1);
    });
  });

  describe("Theming", () => {
    it("initializes with correct theme variables for light mode", async () => {
      document.body.className = "";

      // Setup specific mock for light theme
      window.getComputedStyle.mockReturnValue({
        getPropertyValue: (prop) => {
          if (prop === "--theme-background") return "#ffffff";
          if (prop === "--theme-text") return "#111111";
          return "";
        },
      });

      wrapper = mountComponent();
      await nextTick();

      expect(mermaid.initialize).toHaveBeenCalledOnce();
      const callArgs = vi.mocked(mermaid.initialize).mock.calls[0][0];

      expect(callArgs.theme).toBe("base");
      expect(callArgs.darkMode).toBe(false);
      expect(callArgs.themeVariables.background).toBe("#ffffff");
      expect(callArgs.themeVariables.textColor).toBe("#111111");
    });

    it("initializes with correct theme variables for dark mode", async () => {
      document.body.className = "dark";

      // Setup specific mock for dark theme
      window.getComputedStyle.mockReturnValue({
        getPropertyValue: (prop) => {
          if (prop === "--theme-background") return "#121212";
          if (prop === "--theme-text") return "#eeeeee";
          return "";
        },
      });

      wrapper = mountComponent();
      await nextTick();

      expect(mermaid.initialize).toHaveBeenCalledOnce();
      const callArgs = vi.mocked(mermaid.initialize).mock.calls[0][0];

      expect(callArgs.darkMode).toBe(true);
      expect(callArgs.themeVariables.background).toBe("#121212");
      expect(callArgs.themeVariables.textColor).toBe("#eeeeee");
    });
  });
});
