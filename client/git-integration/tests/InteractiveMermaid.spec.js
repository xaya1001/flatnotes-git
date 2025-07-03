// client/git-integration/tests/InteractiveMermaid.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import mermaid from "mermaid";
import InteractiveMermaid from "../../components/toastui/InteractiveMermaid.vue";

// Use vi.mock to replace the entire module. The implementation will be provided in beforeEach.
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(), // No implementation here, just a spy
  },
}));

// Mock Clipboard API remains the same
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
    // Reset mocks AND provide a fresh, reliable implementation
    // for mermaid.render before each test runs.
    vi.clearAllMocks();
    vi.mocked(mermaid.render).mockResolvedValue({
      svg: `<svg class="mermaid-svg">mocked svg</svg>`,
      bindFunctions: vi.fn(),
    });

    // Mock getComputedStyle for theme tests
    vi.spyOn(window, "getComputedStyle").mockReturnValue({
      getPropertyValue: (prop) => {
        switch (prop) {
          case "--theme-background":
            return "#ffffff";
          case "--theme-text":
            return "#111111";
          case "--theme-border":
            return "#dddddd";
          case "--theme-background-elevated":
            return "#f0f0f0";
          default:
            return "";
        }
      },
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
      await nextTick();
      await nextTick();

      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.exists()).toBe(true);
      expect(mermaid.render).toHaveBeenCalledOnce();
    });

    it("displays an error message if Mermaid rendering fails", async () => {
      // Override the mock for this specific test
      vi.mocked(mermaid.render).mockRejectedValue(new Error("Syntax error"));
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      wrapper = mountComponent();
      await nextTick();
      await nextTick();

      const errorBox = wrapper.find(".mermaid-error-box");
      expect(errorBox.exists()).toBe(true);
      expect(errorBox.text()).toContain("Mermaid Render Error");
      expect(errorBox.text()).toContain("Syntax error");

      consoleErrorSpy.mockRestore();
    });

    it("re-renders when the diagramText prop changes", async () => {
      wrapper = mountComponent();
      await nextTick();
      await nextTick();

      // Clear mocks after initial render to test the second call
      vi.clearAllMocks();
      // Re-apply a mock for the second render
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
      wrapper = mountComponent();
      await nextTick();

      expect(mermaid.initialize).toHaveBeenCalledOnce();
      const callArgs = vi.mocked(mermaid.initialize).mock.calls[0][0];

      expect(callArgs.theme).toBe("base");
      expect(callArgs.darkMode).toBe(false);
      expect(callArgs.suppressErrorRendering).toBe(true);

      const themeVars = callArgs.themeVariables;
      expect(themeVars.background).toBe("#ffffff");
      expect(themeVars.textColor).toBe("#111111");
    });

    it("initializes with correct theme variables for dark mode", async () => {
      document.body.className = "dark";

      window.getComputedStyle.mockReturnValue({
        getPropertyValue: (prop) => {
          switch (prop) {
            case "--theme-background":
              return "#121212";
            case "--theme-text":
              return "#eeeeee";
            default:
              return "";
          }
        },
      });

      wrapper = mountComponent();
      await nextTick();

      expect(mermaid.initialize).toHaveBeenCalledOnce();
      const callArgs = vi.mocked(mermaid.initialize).mock.calls[0][0];

      expect(callArgs.darkMode).toBe(true);
      const themeVars = callArgs.themeVariables;
      expect(themeVars.background).toBe("#121212");
      expect(themeVars.textColor).toBe("#eeeeee");
    });
  });
});
