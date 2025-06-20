// client/git-integration/stores/actionsStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import * as gitApi from "../gitApi";
import { useLogStore } from "./logStore";
import { useStatusStore } from "./statusStore";
import { useHistoryStore } from "./historyStore";
import { usePanelUiStore } from "./panelUiStore";
import { useConflictStore } from "./conflictStore";

export const useActionsStore = defineStore("git-actions", () => {
  const toast = useToast();
  const logStore = useLogStore();
  const statusStore = useStatusStore();
  const historyStore = useHistoryStore();
  const panelUiStore = usePanelUiStore();
  const conflictStore = useConflictStore();

  const isActionLoading = ref(false);
  const isAutoSyncPaused = ref(false);

  async function refreshAllStores() {
    await Promise.all([statusStore.fetchStatus(), historyStore.fetchGitLog()]);
  }

  // This helper is for simple actions that don't have complex error states like conflicts.
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
      await refreshAllStores();
      return true;
    } catch (err) {
      const errorData = err.response?.data?.detail;
      // Special handling for 409 errors
      if (err.response?.status === 409 && errorData?.state) {
        if (errorData.state === "PUSH_REJECTED_NON_FAST_FORWARD") {
          logStore.updateLog(pendingLogId, {
            level: "warn",
            message: `Failed: ${actionName} - Push Rejected`,
            details: errorData.message,
          });
          toast.add({
            severity: "warn",
            summary: "Push Rejected",
            detail: "The remote has changes you need to pull first.",
            life: 6000,
          });
        } else {
          // Generic 409 handler for other conflicts
          logStore.updateLog(pendingLogId, {
            level: "error",
            message: `Failed: ${actionName} - Conflict`,
            details: errorData.message || "An unknown conflict occurred.",
          });
          toast.add({
            severity: "error",
            summary: `Conflict: ${actionName}`,
            detail: errorData.message || "An unknown conflict occurred.",
            life: 5000,
          });
        }
      } else {
        // Generic error handler for non-409 errors
        const errorMessage = errorData?.message || errorData || err.message;
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
      }
      await refreshAllStores(); // Refresh even on failure to show the resulting state
      return false;
    } finally {
      isActionLoading.value = false;
    }
  }

  // --- handlers for complex actions like sync and pull ---

  async function handleSync() {
    const message = statusStore.commitMessage;
    isActionLoading.value = true;
    const pendingLogId = logStore.addPendingLog("Commit & Sync...");
    try {
      const response = await gitApi.gitSyncWorkspace(message);
      toast.add({
        severity: "success",
        summary: "Success",
        detail: "Workspace synced.",
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: "Workspace synced.",
        details: response.details,
      });
      statusStore.clearCommitMessage();
      await refreshAllStores();
    } catch (err) {
      const errorData = err.response?.data?.detail;
      // Check for a 409 conflict and dispatch to the correct handler.
      if (err.response?.status === 409 && errorData?.state) {
        if (errorData.state.includes("CONFLICT")) {
          logStore.updateLog(pendingLogId, {
            level: "warn",
            message: `Sync failed: ${errorData.state}.`,
            details: errorData.message,
          });
          conflictStore.enterConflictMode(errorData);
          statusStore.fetchStatus();
        } else if (errorData.state === "PUSH_REJECTED_NON_FAST_FORWARD") {
          logStore.updateLog(pendingLogId, {
            level: "warn",
            message: "Sync partially failed: Push rejected.",
            details: errorData.message,
          });
          toast.add({
            severity: "warn",
            summary: "Push Rejected",
            detail: "The remote has changes you need to pull first.",
            life: 6000,
          });
          await refreshAllStores(); // Refresh to show the new ahead/behind state
        } else {
          // Handle other potential 409 errors if they arise
          const errorMessage = errorData?.message || errorData || err.message;
          toast.add({
            severity: "error",
            summary: "Sync Error",
            detail: errorMessage,
            life: 5000,
          });
          logStore.updateLog(pendingLogId, {
            level: "error",
            message: "Sync failed with unknown 409 error.",
            details: errorMessage,
          });
          await refreshAllStores();
        }
      } else {
        const errorMessage = errorData?.message || errorData || err.message;
        toast.add({
          severity: "error",
          summary: "Error: Commit & Sync",
          detail: errorMessage,
          life: 5000,
        });
        logStore.updateLog(pendingLogId, {
          level: "error",
          message: "Failed: Commit & Sync",
          details: errorMessage,
        });
        await refreshAllStores(); // Refresh to show the resulting state
      }
    } finally {
      isActionLoading.value = false;
    }
  }

  async function handlePull() {
    isActionLoading.value = true;
    const pendingLogId = logStore.addPendingLog("Pulling changes...");
    try {
      const response = await gitApi.gitPull();
      toast.add({
        severity: "success",
        summary: "Success",
        detail: "Pull operation completed.",
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: "Pull completed.",
        details: response.stdout,
      });
      await refreshAllStores();
    } catch (err) {
      const errorData = err.response?.data?.detail;
      if (
        err.response?.status === 409 &&
        errorData?.state?.includes("CONFLICT")
      ) {
        logStore.updateLog(pendingLogId, {
          level: "warn",
          message: `Pull failed: ${errorData.state}.`,
          details: errorData.message,
        });
        conflictStore.enterConflictMode(errorData);
        statusStore.fetchStatus();
      } else {
        const errorMessage = errorData?.message || errorData || err.message;
        toast.add({
          severity: "error",
          summary: "Error: Pull",
          detail: errorMessage,
          life: 5000,
        });
        logStore.updateLog(pendingLogId, {
          level: "error",
          message: "Failed: Pull",
          details: errorMessage,
        });
        await refreshAllStores();
      }
    } finally {
      isActionLoading.value = false;
    }
  }

  // --- Other action handlers ---

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

  async function getBranches() {
    try {
      // Backend now fetches before listing, so this is correct.
      return await gitApi.getBranches();
    } catch (error) {
      toast.add({
        severity: "error",
        summary: "Error Fetching Branches",
        detail: error.response?.data?.detail || "Could not load branches.",
        life: 4000,
      });
      return { branches: [], current_branch: "Error" };
    }
  }

  function switchBranch(branchName) {
    performGitAction(
      gitApi.switchBranch,
      [branchName],
      "Switch Branch",
      `Switched to branch '${branchName}'.`,
    );
  }

  async function handleResetToRemote() {
    const confirmed = await panelUiStore.showConfirmation({
      title: "Confirm Hard Reset",
      message:
        "This will permanently delete all unpushed commits and any uncommitted changes in your workspace. This action cannot be undone. Are you sure you want to match the remote state?",
      confirmButtonText: "Yes, Reset My Branch",
      confirmButtonStyle: "danger",
    });

    if (confirmed) {
      await performGitAction(
        gitApi.gitResetToRemote,
        [],
        "Reset to Remote",
        "Local branch has been reset to match the remote.",
      );
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
    getBranches,
    switchBranch,
    handleResetToRemote,
    performGitAction,
  };
});
