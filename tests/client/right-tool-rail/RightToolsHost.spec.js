import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RightToolsHost from "../../../client/right-tool-rail/components/RightToolsHost.vue";

const routeState = vi.hoisted(() => ({
  name: "note",
  params: { title: "Example" },
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useRoute: () => routeState,
  };
});

vi.mock(
  "../../../client/git-integration/composables/useGitIntegration.js",
  () => ({
    useGitIntegration: vi.fn(),
  }),
);

vi.mock("../../../client/note-outline/composables/useNoteOutline.js", () => ({
  useNoteOutline: vi.fn(),
}));

const stubs = {
  GitSidebar: { template: '<aside data-test="git-sidebar"></aside>' },
  GitStatusIndicator: {
    template: '<button data-test="git-indicator"></button>',
  },
  OutlineSidebar: { template: '<aside data-test="outline-sidebar"></aside>' },
  OutlineIndicator: {
    template: '<button data-test="outline-indicator"></button>',
  },
  RightToolRail: {
    template: '<nav data-test="right-tool-rail"><slot /></nav>',
    props: ["activePanelWidth"],
  },
};

describe("RightToolsHost.vue", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    routeState.name = "note";
    routeState.params = { title: "Example" };
  });

  function mountHost(props = {}) {
    return mount(RightToolsHost, {
      props,
      global: {
        plugins: [createPinia()],
        stubs,
      },
    });
  }

  it("shows the note outline on note pages when Git is disabled", () => {
    const wrapper = mountHost({ gitEnabled: false });

    expect(wrapper.find('[data-test="right-tool-rail"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="outline-indicator"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="outline-sidebar"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="git-indicator"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="git-sidebar"]').exists()).toBe(false);
  });

  it("keeps the rail hidden away from notes when Git is disabled", () => {
    routeState.name = "home";
    routeState.params = {};

    const wrapper = mountHost({ gitEnabled: false });

    expect(wrapper.find('[data-test="right-tool-rail"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="outline-indicator"]').exists()).toBe(
      false,
    );
    expect(wrapper.find('[data-test="git-indicator"]').exists()).toBe(false);
  });

  it("shows Git controls independently from the note outline", () => {
    routeState.name = "home";
    routeState.params = {};

    const wrapper = mountHost({ gitEnabled: true });

    expect(wrapper.find('[data-test="right-tool-rail"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="git-indicator"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="git-sidebar"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="outline-indicator"]').exists()).toBe(
      false,
    );
  });
});
