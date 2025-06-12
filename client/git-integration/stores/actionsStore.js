// client/git-integration/stores/actionsStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import * as gitApi from "../gitApi";
import { useLogStore } from "./logStore";
import { useStatusStore } from "./statusStore";
import { useHistoryStore } from "./historyStore";
import { usePanelUiStore } from "./panelUiStore";

/**
 * Manages the execution of Git actions (commit, push, pull, etc.),
 * loading states, and auto-sync controls.
 */
export const useActionsStore = defineStore("git-actions", () => {
  // -- DEPS --
  const toast = useToast();
  const logStore = useLogStore();
  const statusStore = useStatusStore();
  const historyStore = useHistoryStore();
  const panelUiStore = usePanelUiStore();

  // -- STATE --
  const isActionLoading = ref(false);
  const isAutoSyncPaused = ref(false);

  // -- PRIVATE WRAPPER --
  async function performGitAction(
    actionFunc,
    args,
    actionName,
    successMessage,
  ) {
    isActionLoading.value = true;
    const pendingLogId = logStore.addPendingLog(`${actionName}...`);
    try {
      const response = await actionFunc(...args);
      toast.add({
        severity: "success",
        summary: "Success",
        detail: successMessage,
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: successMessage,
        details: response.stdout || response.message || null,
      });

      // Refresh relevant data after any action
      await statusStore.fetchStatus();
      await statusStore.fetchStatusSummary();

      if (
        actionName.includes("Commit") ||
        actionName.includes("Sync") ||
        actionName.includes("Pull") ||
        actionName.includes("Discard")
      ) {
        await historyStore.fetchGitLog();
      }
      return true; // Indicate success
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      toast.add({
        severity: "error",
        summary: `Error: ${actionName}`,
        detail: errorMessage,
        life: 5000,
      });
      logStore.updateLog(pendingLogId, {
        level: "error",
        message: `Failed: ${actionName}`,
        details: errorMessage,
      });
      return false; // Indicate failure
    } finally {
      isActionLoading.value = false;
    }
  }

  // -- ACTIONS --
  function handleStageFile(filepath) {
    performGitAction(
      gitApi.gitStageFile,
      [filepath],
      "Stage File",
      `File '${filepath}' staged.`,
    );
  }

  function handleStageAll() {
    performGitAction(gitApi.gitAddAll, [], "Stage All", "All changes staged.");
  }

  function handleUnstageFile(filepath) {
    performGitAction(
      gitApi.gitUnstageFile,
      [filepath],
      "Unstage File",
      `File '${filepath}' unstaged.`,
    );
  }

  function handleUnstageAll() {
    performGitAction(
      gitApi.gitUnstageAll,
      [],
      "Unstage All",
      "All staged changes unstaged.",
    );
  }

  async function handleDiscardFile(filepath) {
    const confirmed = await panelUiStore.showConfirmation({
      title: "Confirm Discard",
      message: `Discard changes to '${filepath}'? This cannot be undone.`,
      confirmButtonText: "Discard",
    });
    if (confirmed) {
      performGitAction(
        gitApi.gitDiscardFile,
        [filepath],
        "Discard File",
        `Changes to '${filepath}' discarded.`,
      );
    }
  }

  async function handleDiscardAll() {
    const confirmed = await panelUiStore.showConfirmation({
      title: "Confirm Discard All",
      message: `Discard ALL unstaged changes? This will delete new files and cannot be undone.`,
      confirmButtonText: "Discard All",
    });
    if (confirmed) {
      performGitAction(
        gitApi.gitDiscardAll,
        [],
        "Discard All",
        "All unstaged changes discarded.",
      );
    }
  }

  async function handleCommit() {
    const message = statusStore.commitMessage;
    if (!message.trim()) return;
    const success = await performGitAction(
      gitApi.gitCommit,
      [message],
      "Commit",
      "Changes committed.",
    );
    if (success) {
      statusStore.clearCommitMessage();
    }
  }

  async function handleSync() {
    const message = statusStore.commitMessage;
    const success = await performGitAction(
      gitApi.gitSyncWorkspace,
      [message],
      "Commit & Sync",
      "Workspace synced.",
    );
    if (success) {
      statusStore.clearCommitMessage();
    }
  }

  function handlePull() {
    performGitAction(gitApi.gitPull, [], "Pull", "Pull operation completed.");
  }

  function handlePush() {
    performGitAction(gitApi.gitPush, [], "Push", "Push operation completed.");
  }

  async function fetchAutoSyncState() {
    try {
      const state = await gitApi.getAutoSyncState();
      isAutoSyncPaused.value = state.paused;
    } catch (error) {
      console.error("Failed to get initial auto-sync state", error);
    }
  }

  async function toggleAutoSyncPause() {
    const action = isAutoSyncPaused.value
      ? gitApi.resumeAutoSync
      : gitApi.pauseAutoSync;
    const actionName = isAutoSyncPaused.value
      ? "Resume Auto-Sync"
      : "Pause Auto-Sync";
    const successMessage = `Auto-sync ${isAutoSyncPaused.value ? "resumed" : "paused"}.`;

    isActionLoading.value = true;
    const pendingLogId = logStore.addPendingLog(`${actionName}...`);
    try {
      const response = await action();
      isAutoSyncPaused.value = response.paused;
      toast.add({
        severity: "info",
        summary: "Auto-Sync",
        detail: successMessage,
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: successMessage,
      });
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail || "Failed to update auto-sync state.";
      toast.add({
        severity: "error",
        summary: "Error",
        detail: errorMessage,
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "error",
        message: `Failed: ${actionName}`,
        details: errorMessage,
      });
    } finally {
      isActionLoading.value = false;
    }
  }

  return {
    isActionLoading,
    isAutoSyncPaused,
    handleStageFile,
    handleStageAll,
    handleUnstageFile,
    handleUnstageAll,
    handleDiscardFile,
    handleDiscardAll,
    handleCommit,
    handleSync,
    handlePull,
    handlePush,
    fetchAutoSyncState,
    toggleAutoSyncPause,
  };
});
