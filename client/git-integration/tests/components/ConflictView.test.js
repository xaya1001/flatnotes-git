// client/git-integration/tests/components/ConflictView.test.js

import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import ToastService from "primevue/toastservice";
import ConflictView from "../../components/tabs/ConflictView.vue";
import { useStatusStore } from "../../stores/statusStore";
import { usePanelUiStore } from "../../stores/panelUiStore";
import { useConflictStore } from "../../stores/conflictStore";
import { routerKey } from "vue-router"; // Import the key used by vue-router

// A helper function to mount the component and set up state correctly.
const mountComponentWithState = (initialState = {}) => {
  const pinia = createPinia();

  const wrapper = mount(ConflictView, {
    global: {
      plugins: [pinia, ToastService],
      // Provide a mock router to satisfy the dependency injection for useStatusStore
      // This eliminates the "[Vue warn]: injection not found" message.
      provide: {
        [routerKey]: {
          push: vi.fn(),
        },
      },
      stubs: {
        FileTable: true,
        SvgIcon: true,
      },
    },
  });

  // Access the stores *after* mounting has successfully provided the plugins.
  const statusStore = useStatusStore();
  const panelUiStore = usePanelUiStore();
  const conflictStore = useConflictStore();

  // Apply the desired initial state for the test case
  statusStore.repositoryState = initialState.repositoryState || "CLEAN";
  statusStore.gitStatus.files = initialState.files || [];

  return { wrapper, statusStore, panelUiStore, conflictStore };
};

describe("ConflictView.vue", () => {
  // ----- Rendering Tests -----

  it("renders correctly for a REBASE conflict", async () => {
    const { wrapper } = mountComponentWithState({
      repositoryState: "REBASING_CONFLICT",
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.find("h2").text()).toContain(
      "Resolve Conflicts to Continue Rebase",
    );
    expect(wrapper.find("button.bg-theme-success").text()).toBe(
      "Continue Rebase",
    );
    expect(wrapper.find("button.bg-theme-danger").text()).toBe("Abort Rebase");
  });

  it("renders correctly for a MERGE conflict", async () => {
    const { wrapper } = mountComponentWithState({
      repositoryState: "MERGING_CONFLICT",
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.find("h2").text()).toContain(
      "Resolve Conflicts to Continue Merge",
    );
    expect(wrapper.find("button.bg-theme-success").text()).toBe(
      "Continue Merge",
    );
    expect(wrapper.find("button.bg-theme-danger").text()).toBe("Abort Merge");
  });

  it('disables "Continue" button when state is REBASING_CONFLICT', async () => {
    const { wrapper } = mountComponentWithState({
      repositoryState: "REBASING_CONFLICT",
    });
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find("button.bg-theme-success").attributes("disabled"),
    ).toBeDefined();
  });

  it('enables "Continue" button for REBASING_CONTINUE with no unstaged files', async () => {
    const { wrapper } = mountComponentWithState({
      repositoryState: "REBASING_CONTINUE",
      files: [
        { path: "resolved.md", work_tree_status: " ", index_status: "A" },
      ],
    });
    await wrapper.vm.$nextTick();
    expect(
      wrapper.find("button.bg-theme-success").attributes("disabled"),
    ).toBeUndefined();
  });

  // ----- Interaction Tests -----

  describe("User Interactions", () => {
    it('calls confirmation and then continue action when "Continue" is clicked and confirmed', async () => {
      const { wrapper, panelUiStore, conflictStore } = mountComponentWithState({
        repositoryState: "REBASING_CONTINUE",
      });

      const showConfirmationSpy = vi
        .spyOn(panelUiStore, "showConfirmation")
        .mockResolvedValue(true);
      const handleContinueSpy = vi
        .spyOn(conflictStore, "handleContinue")
        .mockResolvedValue();

      await wrapper.vm.$nextTick();
      await wrapper.find("button.bg-theme-success").trigger("click");

      expect(showConfirmationSpy).toHaveBeenCalledOnce();
      expect(handleContinueSpy).toHaveBeenCalledOnce();
    });

    it('calls confirmation but not continue action when "Continue" is clicked and cancelled', async () => {
      const { wrapper, panelUiStore, conflictStore } = mountComponentWithState({
        repositoryState: "REBASING_CONTINUE",
      });

      const showConfirmationSpy = vi
        .spyOn(panelUiStore, "showConfirmation")
        .mockResolvedValue(false);
      const handleContinueSpy = vi.spyOn(conflictStore, "handleContinue");

      await wrapper.vm.$nextTick();
      await wrapper.find("button.bg-theme-success").trigger("click");

      expect(showConfirmationSpy).toHaveBeenCalledOnce();
      expect(handleContinueSpy).not.toHaveBeenCalled();
    });

    it('calls confirmation and then abort action when "Abort" is clicked and confirmed', async () => {
      const { wrapper, panelUiStore, conflictStore } = mountComponentWithState({
        repositoryState: "REBASING_CONFLICT",
      });

      const showConfirmationSpy = vi
        .spyOn(panelUiStore, "showConfirmation")
        .mockResolvedValue(true);
      const handleAbortSpy = vi
        .spyOn(conflictStore, "handleAbort")
        .mockResolvedValue();

      await wrapper.vm.$nextTick();
      await wrapper.find("button.bg-theme-danger").trigger("click");

      expect(showConfirmationSpy).toHaveBeenCalledOnce();
      expect(handleAbortSpy).toHaveBeenCalledOnce();
    });
  });
});
