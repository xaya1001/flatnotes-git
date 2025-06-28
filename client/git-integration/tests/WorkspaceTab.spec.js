// client/git-integration/tests/WorkspaceTab.spec.js

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useGitOperation } from "../composables/useGitOperation.js";

// --- MOCKING AREA ---

// 1. Mock the composable we are not testing directly
vi.mock("../composables/useGitOperation.js", () => ({
  useGitOperation: vi.fn(() => ({
    isLoading: { value: false },
    execute: vi.fn(() => Promise.resolve()),
  })),
}));

// 2. Partially mock the vue-router module
const mockRouterPush = vi.fn();
vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal(); // Import the original module
  return {
    ...actual, // Keep all original exports
    useRouter: () => ({
      // Override only the useRouter export
      push: mockRouterPush,
    }),
  };
});

// --- END MOCKING AREA ---

import WorkspaceTab from "../components/tabs/WorkspaceTab.vue";
import { useStatusStore } from "../stores/statusStore";

const stubs = {
  FileTable: true,
  SvgIcon: true,
  OverlayPanel: true,
};

describe("WorkspaceTab.vue", () => {
  let statusStore;

  beforeEach(() => {
    setActivePinia(createPinia());
    statusStore = useStatusStore();
    statusStore.commitMessage = "chore: sync {{num}} notes at {{datetime}}";
    vi.clearAllMocks();
  });

  const mountComponent = () => {
    return mount(WorkspaceTab, {
      global: {
        stubs,
      },
    });
  };

  it("disables Pull button if there are uncommitted changes", () => {
    statusStore.gitStatus = {
      files: [{ path: "note.md", work_tree_status: "M", index_status: " " }],
    };
    const wrapper = mountComponent();
    const pullButton = wrapper.find('button[title*="Commit or discard"]');
    expect(pullButton.exists()).toBe(true);
    expect(pullButton.attributes("disabled")).toBeDefined();
  });

  it("disables Pull button if branch is not tracking upstream", () => {
    statusStore.$patch({ isTrackingUpstream: false });
    const wrapper = mountComponent();
    const pullButton = wrapper.find('button[title*="not tracking"]');
    expect(pullButton.exists()).toBe(true);
    expect(pullButton.attributes("disabled")).toBeDefined();
  });

  it("enables Pull button when workspace is clean and behind remote", () => {
    statusStore.$patch({
      isTrackingUpstream: true,
      commitsBehind: 2,
      gitStatus: { files: [] },
    });
    const wrapper = mountComponent();
    const pullButton = wrapper.find('button[title*="Pull 2 commits"]');
    expect(pullButton.exists()).toBe(true);
    expect(pullButton.attributes("disabled")).toBeUndefined();
  });

  it("calls the sync operation when 'Commit & Sync' is clicked", async () => {
    statusStore.$patch({
      commitMessage: "Test commit",
      gitStatus: { files: [{ path: "note.md", work_tree_status: "M" }] },
    });
    const mockSyncExecute = vi.fn(() => Promise.resolve());
    useGitOperation.mockImplementation((actionName) => {
      if (actionName === "Commit & Sync") {
        return { isLoading: { value: false }, execute: mockSyncExecute };
      }
      return { isLoading: { value: false }, execute: vi.fn() };
    });
    const wrapper = mountComponent();
    await wrapper.find("button.bg-theme-brand").trigger("click");
    expect(useGitOperation).toHaveBeenCalledWith(
      "Commit & Sync",
      expect.any(Function),
    );
    expect(mockSyncExecute).toHaveBeenCalledWith("Test commit");
  });

  it("resets commit message to default on successful sync", async () => {
    statusStore.$patch({
      commitMessage: "A custom user message",
      gitStatus: { files: [{ path: "note.md", work_tree_status: "M" }] },
    });
    const mockSyncExecute = vi.fn(() => Promise.resolve());
    useGitOperation.mockImplementation((actionName) => ({
      isLoading: { value: false },
      execute: actionName === "Commit & Sync" ? mockSyncExecute : vi.fn(),
    }));
    const wrapper = mountComponent();
    await wrapper.find("button.bg-theme-brand").trigger("click");

    expect(statusStore.commitMessage).toBe(
      "chore: sync {{num}} notes at {{datetime}}",
    );
  });
});
