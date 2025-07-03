// client/git-integration/tests/InteractiveMermaid.spec.js

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount } from "@vue/test-utils";
import mermaid from "mermaid";
import InteractiveMermaid from "../../components/toastui/InteractiveMermaid.vue";

// --- Helper Function for Async DOM updates ---
// This function polls the DOM until a condition is met or it times out.
// This is more robust than relying on a single nextTick for complex updates like v-html.
function waitFor(callback, { timeout = 1000, interval = 50 } = {}) {
  return new Promise((resolve, reject) => {
    let lastError;
    const endTime = Date.now() + timeout;

    const check = () => {
      try {
        const result = callback();
        // If the callback doesn't throw, we've succeeded.
        resolve(result);
      } catch (e) {
        lastError = e;
        if (Date.now() < endTime) {
          setTimeout(check, interval);
        } else {
          console.error("waitFor timed out. Last error:", lastError.message);
          reject(
            new Error(`waitFor timed out. Last error: ${lastError.message}`),
          );
        }
      }
    };
    check();
  });
}

// --- Mocking Area ---
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockImplementation((id, text) => {
      return Promise.resolve({
        svg: `<svg id="${id}" class="mermaid-svg">${text}</svg>`,
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

      // Use the robust waitFor helper instead of a single nextTick.
      await waitFor(() => {
        const svgElement = wrapper.find("svg.mermaid-svg");
        expect(svgElement.exists()).toBe(true);
      });

      expect(mermaid.render).toHaveBeenCalledOnce();
      expect(mermaid.render).toHaveBeenCalledWith(
        expect.stringMatching(/^mermaid-id-/),
        "graph TD; A-->B;",
      );

      const svgElement = wrapper.find("svg.mermaid-svg");
      expect(svgElement.text()).toBe("graph TD; A-->B;");
    });

    it("displays an error message if Mermaid rendering fails", async () => {
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const errorMessage = "Syntax error in graph";
      mermaid.render.mockRejectedValueOnce(new Error(errorMessage));

      wrapper = mountComponent();

      // Use waitFor to ensure the error message is rendered.
      await waitFor(() => {
        const errorBox = wrapper.find(".mermaid-error-box");
        expect(errorBox.exists()).toBe(true);
      });

      const errorBox = wrapper.find(".mermaid-error-box");
      expect(errorBox.text()).toContain("Mermaid Render Error");
      expect(errorBox.text()).toContain(errorMessage);

      consoleErrorSpy.mockRestore();
    });

    it("re-renders when the diagramText prop changes", async () => {
      wrapper = mountComponent();
      await waitFor(() => {
        expect(wrapper.find("svg.mermaid-svg").exists()).toBe(true);
      });
      expect(mermaid.render).toHaveBeenCalledTimes(1);

      await wrapper.setProps({ diagramText: "graph LR; C-->D;" });

      await waitFor(() => {
        const svgElement = wrapper.find("svg.mermaid-svg");
        expect(svgElement.text()).toBe("graph LR; C-->D;");
      });

      expect(mermaid.render).toHaveBeenCalledTimes(2);
      expect(mermaid.render).toHaveBeenLastCalledWith(
        expect.stringMatching(/^mermaid-id-/),
        "graph LR; C-->D;",
      );
    });
  });

  describe("User Interaction", () => {
    beforeEach(async () => {
      wrapper = mountComponent();
      await waitFor(() => {
        expect(wrapper.find(".svg-wrapper").exists()).toBe(true);
      });
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
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      expect(wrapper.vm.scale).toBeGreaterThan(initialScale);
    });

    it("zooms out when zoom-out button is clicked", async () => {
      const initialScale = wrapper.vm.scale;
      await wrapper.find('button[title="Zoom Out"]').trigger("click");
      expect(wrapper.vm.scale).toBeLessThan(initialScale);
    });

    it("resets view when reset button is clicked", async () => {
      // Change state
      await wrapper.find('button[title="Zoom In"]').trigger("click");
      wrapper.vm.panX = 50;
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.scale).not.toBe(1);
      expect(wrapper.vm.panX).not.toBe(0);

      // Act: reset
      await wrapper.find('button[title="Reset View"]').trigger("click");

      // Assert
      expect(wrapper.vm.scale).toBe(1);
      expect(wrapper.vm.panX).toBe(0);
      expect(wrapper.vm.panY).toBe(0);
    });
  });

  describe("Theming", () => {
    it("initializes with the default theme when body has no dark class", async () => {
      document.body.className = "";
      wrapper = mountComponent();
      await waitFor(() => {
        expect(mermaid.initialize).toHaveBeenCalled();
      });

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({
          theme: "default",
        }),
      );
    });

    it("initializes with the dark theme when body has a dark class", async () => {
      document.body.className = "dark";
      wrapper = mountComponent();
      await waitFor(() => {
        expect(mermaid.initialize).toHaveBeenCalled();
      });

      expect(mermaid.initialize).toHaveBeenCalledWith(
        expect.objectContaining({
          theme: "dark",
        }),
      );
    });
  });
});
