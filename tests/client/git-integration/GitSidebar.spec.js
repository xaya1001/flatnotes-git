import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import GitSidebar from "../../../client/git-integration/components/GitSidebar.vue";
import { useStatusStore } from "../../../client/git-integration/stores/statusStore.js";
import { usePanelUiStore } from "../../../client/git-integration/stores/panelUiStore.js";
import { useHistoryStore } from "../../../client/git-integration/stores/historyStore.js";
import { useLogStore } from "../../../client/git-integration/stores/logStore.js";

// --- PrimeVue and Global Mocks ---
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";

vi.mock("primevue/usetoast", () => ({
  useToast: () => ({ add: vi.fn() }),
}));

vi.mock("../../../client/git-integration/gitApi.js", () => ({
  getGitStatus: vi.fn(),
  getGitLog: vi.fn().mockResolvedValue({ log: [] }),
  getGitActivityLog: vi.fn().mockResolvedValue([]),
}));

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useRouter: () => ({ push: vi.fn() }) };
});
// --- End Mocks ---

const stubs = {
  Sidebar: { template: "<div><slot/></div>", props: ["visible"] },
  GitStatusIndicator: true,
  ConfirmModal: true,
  WorkspaceTab: { template: '<div id="workspace-tab"></div>' },
  ConflictView: { template: '<div id="conflict-view"></div>' },
  GitHistoryTab: true,
  GitLogTab: true,
  SvgIcon: true,
  TabView: { template: "<div><slot/></div>" },
  TabPanel: { template: '<div><slot name="header"/><slot/></div>' },
};

describe("GitSidebar.vue", () => {
  // Helper function for mounting with required plugins
  const mountComponent = () => {
    return mount(GitSidebar, {
      global: {
        plugins: [createPinia(), PrimeVue, ToastService],
        stubs,
      },
    });
  };

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it("renders WorkspaceTab when state is clean", async () => {
    const wrapper = mountComponent();
    const store = useStatusStore();
    store.isInitialLoadComplete = true;
    store.repositoryState = "CLEAN";

    // Wait for Vue to process the state change and re-render
    await wrapper.vm.$nextTick();

    expect(wrapper.find("#workspace-tab").exists()).toBe(true);
    expect(wrapper.find("#conflict-view").exists()).toBe(false);
  });

  it("renders ConflictView when state is REBASING_CONFLICT", async () => {
    const wrapper = mountComponent();
    const store = useStatusStore();
    store.isInitialLoadComplete = true;
    store.repositoryState = "REBASING_CONFLICT";

    await wrapper.vm.$nextTick();

    expect(wrapper.find("#workspace-tab").exists()).toBe(false);
    expect(wrapper.find("#conflict-view").exists()).toBe(true);
  });

  it("renders the setup guide on specific error", async () => {
    const wrapper = mountComponent();
    const store = useStatusStore();
    store.isInitialLoadComplete = true;
    store.summaryError = "Git repository not initialized";

    await wrapper.vm.$nextTick();

    // Check for the new, user-friendly title
    expect(wrapper.text()).toContain("Connect Your Git Repository");

    // Verify that both setup options are present
    expect(wrapper.text()).toContain("Option 1: Start a New Repository");
    expect(wrapper.text()).toContain(
      "Option 2: Connect an Existing Remote Repo",
    );

    // Ensure the old, less helpful text is gone
    expect(wrapper.text()).not.toContain("Git Repository Not Found");
  });

  it("shows loading state initially", () => {
    const wrapper = mountComponent();
    const store = useStatusStore();
    store.isInitialLoadComplete = false;
    // No need to await here, this is the initial render state
    expect(wrapper.text()).toContain("Loading Git Status...");
  });

  it("calls refreshAll when refresh button is clicked", async () => {
    const wrapper = mountComponent();
    const statusStore = useStatusStore();
    const historyStore = useHistoryStore();
    const logStore = useLogStore();
    const statusSpy = vi.spyOn(statusStore, "fetchStatus").mockResolvedValue();
    const historySpy = vi
      .spyOn(historyStore, "fetchGitLog")
      .mockResolvedValue();
    const logSpy = vi.spyOn(logStore, "fetchActivityLog").mockResolvedValue();

    await wrapper.find('button[title="Refresh all Git data"]').trigger("click");

    expect(statusSpy).toHaveBeenCalled();
    expect(historySpy).toHaveBeenCalled();
    expect(logSpy).toHaveBeenCalled();
  });

  it("toggles pin state when pin button is clicked", async () => {
    const wrapper = mountComponent();
    const panelUiStore = usePanelUiStore();
    const togglePinSpy = vi.spyOn(panelUiStore, "togglePin");

    await wrapper.find('button[title*="Pin Panel"]').trigger("click");
    expect(togglePinSpy).toHaveBeenCalled();
  });

  it("hides the sidebar when close button is clicked", async () => {
    const wrapper = mountComponent();
    const panelUiStore = usePanelUiStore();
    const forceHideSidebarSpy = vi.spyOn(panelUiStore, "forceHideSidebar");

    await wrapper.find('button[title="Close Panel"]').trigger("click");
    expect(forceHideSidebarSpy).toHaveBeenCalled();
  });
});
