// client/git-integration/tests/GitHistoryTab.spec.js

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";

// --- MOCKS ---

// Mock the API module
vi.mock("../gitApi.js", () => ({
  getGitLog: vi.fn().mockResolvedValue({ log: [], remote_base_url: "" }),
  getGitCommitFiles: vi.fn().mockResolvedValue([]),
  gitRestoreFile: vi.fn().mockResolvedValue({}),
  gitResetToRemote: vi.fn().mockResolvedValue({}),
}));

const mockRestoreExecute = vi.fn(() => Promise.resolve());
const mockResetExecute = vi.fn(() => Promise.resolve());

vi.mock("../composables/useGitOperation.js", () => ({
  useGitOperation: vi.fn((actionName) => {
    if (actionName === "Restore File") {
      return { isLoading: { value: false }, execute: mockRestoreExecute };
    }
    if (actionName === "Reset to Remote") {
      return { isLoading: { value: false }, execute: mockResetExecute };
    }
    return { isLoading: { value: false }, execute: vi.fn() };
  }),
}));

// Mock the router
vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// --- END MOCKS ---

import GitHistoryTab from "../components/tabs/GitHistoryTab.vue";
import { useHistoryStore } from "../stores/historyStore";
import { useStatusStore } from "../stores/statusStore";
import { usePanelUiStore } from "../stores/panelUiStore";

const stubs = {
  SvgIcon: true,
  OverlayPanel: {
    template: "<div><slot /></div>",
    methods: { toggle: vi.fn() },
  },
};

const mockCommits = [
  {
    hash: "a1b2c3d",
    message: "feat: Add new feature",
    author_name: "Test User",
    date: new Date().toISOString(),
    is_pushed: true,
  },
  {
    hash: "h8i9j0k",
    message: "fix: Correct a bug (unpushed)",
    author_name: "Test User",
    date: new Date().toISOString(),
    is_pushed: false,
  },
];

describe("GitHistoryTab.vue", () => {
  let wrapper;
  let historyStore, statusStore, panelUiStore;

  // Helper function to mount the component with all necessary setup
  const mountComponent = () => {
    const pinia = createPinia();
    wrapper = mount(GitHistoryTab, {
      global: {
        plugins: [pinia, PrimeVue, ToastService],
        stubs,
      },
    });
    // Get store instances *after* the component is mounted with Pinia
    historyStore = useHistoryStore();
    statusStore = useStatusStore();
    panelUiStore = usePanelUiStore();
  };

  beforeEach(() => {
    setActivePinia(createPinia()); // Set a base pinia instance
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("shows loading skeleton when store is loading", () => {
      mountComponent();
      historyStore.isLoading = true;
      // We need a separate `await` here to let Vue react to the store change
      return wrapper.vm.$nextTick().then(() => {
        expect(wrapper.find(".animate-pulse").exists()).toBe(true);
      });
    });

    it('shows "No commit history found" message when log is empty', async () => {
      mountComponent();
      historyStore.gitLog = [];
      await wrapper.vm.$nextTick();
      expect(wrapper.text()).toContain("No commit history found.");
    });

    it("renders the list of commits correctly", async () => {
      mountComponent();
      historyStore.gitLog = mockCommits;
      await wrapper.vm.$nextTick();

      const commitMessages = wrapper.findAll(".font-semibold");
      expect(commitMessages[0].text()).toBe("feat: Add new feature");
      expect(wrapper.text()).toContain("fix: Correct a bug (unpushed)");
      expect(wrapper.find(".bg-yellow-500").exists()).toBe(true);
    });
  });

  describe("Interaction", () => {
    it("calls toggleCommitExpansion when a commit is clicked", async () => {
      mountComponent();
      historyStore.gitLog = mockCommits;
      await wrapper.vm.$nextTick();

      const toggleSpy = vi.spyOn(historyStore, "toggleCommitExpansion");

      await wrapper.find(".cursor-pointer").trigger("click");
      expect(toggleSpy).toHaveBeenCalledWith(mockCommits[0].hash);
    });

    it("renders commit files when a commit is expanded", async () => {
      mountComponent();
      historyStore.gitLog = mockCommits;
      historyStore.expandedCommit = mockCommits[0].hash;
      historyStore.commitFilesCache = {
        [mockCommits[0].hash]: [{ path: "file1.md", index_status: "A" }],
      };
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain("file1.md");
    });
  });

  describe("Advanced Actions", () => {
    it("calls confirmation and restore function on file restore click", async () => {
      mountComponent();
      const confirmSpy = vi
        .spyOn(panelUiStore, "showConfirmation")
        .mockResolvedValue(true);

      historyStore.gitLog = mockCommits;
      historyStore.expandedCommit = mockCommits[0].hash;
      historyStore.commitFilesCache = {
        [mockCommits[0].hash]: [{ path: "file1.md", index_status: "A" }],
      };
      await wrapper.vm.$nextTick();

      await wrapper.find('button[title*="Restore this file"]').trigger("click");

      expect(confirmSpy).toHaveBeenCalled();
      expect(mockRestoreExecute).toHaveBeenCalledWith(
        mockCommits[0].hash,
        "file1.md",
      );
    });

    it("calls confirmation and reset function on reset click", async () => {
      mountComponent();
      const confirmSpy = vi
        .spyOn(panelUiStore, "showConfirmation")
        .mockResolvedValue(true);
      statusStore.commitsAhead = 1;
      await wrapper.vm.$nextTick();

      await wrapper.find('button[title="Advanced Options"]').trigger("click");
      await wrapper.find("button.border-theme-danger").trigger("click");

      expect(confirmSpy).toHaveBeenCalled();
      expect(mockResetExecute).toHaveBeenCalled();
    });

    it("disables advanced action buttons during a conflict", async () => {
      mountComponent();
      statusStore.repositoryState = "REBASING_CONFLICT";
      historyStore.gitLog = mockCommits;
      historyStore.expandedCommit = mockCommits[0].hash;
      historyStore.commitFilesCache = {
        [mockCommits[0].hash]: [{ path: "file1.md", index_status: "A" }],
      };
      await wrapper.vm.$nextTick();

      const restoreButton = wrapper.find('button[title*="Restore this file"]');
      expect(restoreButton.attributes("disabled")).toBeDefined();
    });
  });
});
