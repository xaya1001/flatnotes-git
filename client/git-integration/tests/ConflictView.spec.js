// client/git-integration/tests/ConflictView.spec.js

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { useGitOperation } from "../composables/useGitOperation.js";

// --- MOCKING AREA ---

vi.mock("../composables/useGitOperation.js", () => ({
  useGitOperation: vi.fn(() => ({
    isLoading: { value: false },
    execute: vi.fn(() => Promise.resolve()),
  })),
}));

// Partially mock vue-router to provide a dummy useRouter
const mockRouterPush = vi.fn();
vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useRouter: () => ({
      push: mockRouterPush,
    }),
  };
});

// --- END MOCKING AREA ---

import ConflictView from "../components/ConflictView.vue";
import { useStatusStore } from "../stores/statusStore";
import { usePanelUiStore } from "../stores/panelUiStore";

const stubs = {
  FileTable: true,
  SvgIcon: true,
};

describe("ConflictView.vue", () => {
  let statusStore;
  let panelUiStore;
  let mockContinueExecute;
  let mockAbortExecute;

  beforeEach(() => {
    setActivePinia(createPinia());
    statusStore = useStatusStore();
    panelUiStore = usePanelUiStore();
    vi.clearAllMocks();

    mockContinueExecute = vi.fn(() => Promise.resolve());
    mockAbortExecute = vi.fn(() => Promise.resolve());

    useGitOperation.mockImplementation((actionName) => {
      if (actionName === "Continue Operation") {
        return { isLoading: { value: false }, execute: mockContinueExecute };
      }
      if (actionName === "Abort Operation") {
        return { isLoading: { value: false }, execute: mockAbortExecute };
      }
      return { isLoading: { value: false }, execute: vi.fn() };
    });
  });

  const mountComponent = () => {
    return mount(ConflictView, {
      global: {
        stubs,
      },
    });
  };

  it("renders correct header for Rebase conflict", () => {
    statusStore.$patch({
      repositoryState: "REBASING_CONFLICT",
      gitStatus: { files: [] },
    });
    const wrapper = mountComponent();
    expect(wrapper.text()).toContain("Resolve Conflicts to Continue Rebase");
  });

  it("renders correct header for Merge conflict", () => {
    statusStore.$patch({
      repositoryState: "MERGING_CONFLICT",
      gitStatus: { files: [] },
    });
    const wrapper = mountComponent();
    expect(wrapper.text()).toContain("Resolve Conflicts to Continue Merge");
  });

  it("disables 'Continue' button when there are unresolved conflicts", () => {
    statusStore.$patch({
      repositoryState: "REBASING_CONFLICT",
      gitStatus: {
        files: [{ path: "a.md", work_tree_status: "U", index_status: "U" }],
      },
    });
    const wrapper = mountComponent();
    const continueButton = wrapper.find(
      'button[title*="You must resolve all conflicts"]',
    );
    expect(continueButton.exists()).toBe(true);
    expect(continueButton.attributes("disabled")).toBeDefined();
  });

  it("enables 'Continue' button when all conflicts are staged", () => {
    statusStore.$patch({
      repositoryState: "REBASING_CONTINUE",
      gitStatus: {
        files: [{ path: "a.md", work_tree_status: " ", index_status: "M" }],
      },
    });
    const wrapper = mountComponent();
    const continueButton = wrapper.find('button[title*="Continue the rebase"]');
    expect(continueButton.exists()).toBe(true);
    expect(continueButton.attributes("disabled")).toBeUndefined();
  });

  it("shows a warning if there are other unstaged changes when ready to continue", () => {
    statusStore.$patch({
      repositoryState: "REBASING_CONTINUE",
      gitStatus: {
        files: [
          { path: "a.md", work_tree_status: " ", index_status: "M" },
          { path: "b.md", work_tree_status: "M", index_status: " " },
        ],
      },
    });
    const wrapper = mountComponent();
    expect(wrapper.text()).toContain("You have unstaged changes");
    const continueButton = wrapper.find(
      'button[title*="You must stage all remaining changes"]',
    );
    expect(continueButton.exists()).toBe(true);
    expect(continueButton.attributes("disabled")).toBeDefined();
  });

  it("calls confirmation and then abort operation on 'Abort' click", async () => {
    const confirmationSpy = vi
      .spyOn(panelUiStore, "showConfirmation")
      .mockResolvedValue(true);

    statusStore.$patch({
      repositoryState: "REBASING_CONFLICT",
      gitStatus: { files: [] },
    });
    const wrapper = mountComponent();

    await wrapper.find('button[title*="Abort the rebase"]').trigger("click");

    expect(confirmationSpy).toHaveBeenCalled();
    expect(mockAbortExecute).toHaveBeenCalled();
  });

  it("does not call abort operation if confirmation is rejected", async () => {
    const confirmationSpy = vi
      .spyOn(panelUiStore, "showConfirmation")
      .mockResolvedValue(false);

    statusStore.$patch({
      repositoryState: "REBASING_CONFLICT",
      gitStatus: { files: [] },
    });
    const wrapper = mountComponent();

    await wrapper.find('button[title*="Abort the rebase"]').trigger("click");

    expect(confirmationSpy).toHaveBeenCalled();
    expect(mockAbortExecute).not.toHaveBeenCalled();
  });
});
