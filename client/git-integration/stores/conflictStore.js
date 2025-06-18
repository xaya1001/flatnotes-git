// client/git-integration/stores/conflictStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import * as gitApi from "../gitApi";
import { useLogStore } from "./logStore";
import { useStatusStore } from "./statusStore";
import { useHistoryStore } from "./historyStore";
import { useActionsStore } from "./actionsStore";

export const useConflictStore = defineStore("git-conflict", () => {
  const toast = useToast();
  const logStore = useLogStore();

  const isInConflict = ref(false);
  const conflictedFiles = ref([]);

  function enterConflictMode(files, options = {}) {
    isInConflict.value = true;
    conflictedFiles.value = files;

    if (!options.silent) {
      toast.add({
        severity: "warn",
        summary: "Sync Conflict",
        detail: "Please resolve the file conflicts to continue.",
        life: 6000,
      });
    }

    logStore.addLog({
      level: "warn",
      message: "Sync conflict detected.",
      details: `Files with conflicts: ${files.join(", ")}`,
    });
  }

  function exitConflictMode() {
    isInConflict.value = false;
    conflictedFiles.value = [];
  }

  async function handleContinue() {
    const actionsStore = useActionsStore();
    actionsStore.isActionLoading = true;
    const pendingLogId = logStore.addPendingLog("Continuing rebase...");
    try {
      const response = await gitApi.gitRebaseContinue();
      toast.add({
        severity: "success",
        summary: "Rebase Complete",
        detail: response.message,
        life: 4000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: "Rebase finished successfully.",
        details: response.details || response.stdout,
      });
      exitConflictMode();
      // Full refresh
      const statusStore = useStatusStore();
      const historyStore = useHistoryStore();
      await Promise.all([
        statusStore.fetchStatus(),
        historyStore.fetchGitLog(),
      ]);
    } catch (err) {
      // Check if it's another conflict
      if (
        err.response?.status === 409 &&
        err.response.data.detail?.state === "REBASE_CONFLICT"
      ) {
        const errorData = err.response.data.detail;
        if (
          errorData.conflicted_files &&
          errorData.conflicted_files.length > 0
        ) {
          toast.add({
            severity: "warn",
            summary: "More Conflicts Found",
            detail: "Please resolve the new conflicts shown.",
            life: 5000,
          });
          logStore.updateLog(pendingLogId, {
            level: "warn",
            message: "Rebase paused with new conflicts.",
            details: errorData.message,
          });
          // Update the conflict state with the new list of files
          isInConflict.value = true;
          conflictedFiles.value = errorData.conflicted_files;
        } else {
          // Edge case: 409 conflict but no files listed. Assume success and refresh.
          toast.add({
            severity: "success",
            summary: "Rebase Step Complete",
            detail: "Rebase step completed. Checking final status.",
            life: 4000,
          });
          logStore.updateLog(pendingLogId, {
            level: "success",
            message:
              "Rebase step finished (recovered from inconsistent state).",
          });
          exitConflictMode();
          // Full refresh to get the real state
          const statusStore = useStatusStore();
          const historyStore = useHistoryStore();
          await Promise.all([
            statusStore.fetchStatus(),
            historyStore.fetchGitLog(),
          ]);
        }
      } else {
        const errorMessage =
          err.response?.data?.detail?.message ||
          err.response?.data?.detail ||
          err.message;
        toast.add({
          severity: "error",
          summary: "Rebase Failed",
          detail: errorMessage,
          life: 5000,
        });
        logStore.updateLog(pendingLogId, {
          level: "error",
          message: "Failed to continue rebase.",
          details: errorMessage,
        });
      }
    } finally {
      actionsStore.isActionLoading = false;
    }
  }

  async function handleAbort() {
    const actionsStore = useActionsStore();
    actionsStore.isActionLoading = true;
    const pendingLogId = logStore.addPendingLog("Aborting rebase...");
    try {
      const response = await gitApi.gitRebaseAbort();
      toast.add({
        severity: "info",
        summary: "Rebase Aborted",
        detail: "The repository has been returned to its previous state.",
        life: 4000,
      });
      logStore.updateLog(pendingLogId, {
        level: "warn",
        message: "Rebase aborted by user.",
        details: response.stdout,
      });
      exitConflictMode();
      // Full refresh
      const statusStore = useStatusStore();
      const historyStore = useHistoryStore();
      await Promise.all([
        statusStore.fetchStatus(),
        historyStore.fetchGitLog(),
      ]);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      toast.add({
        severity: "error",
        summary: "Abort Failed",
        detail: errorMessage,
        life: 5000,
      });
      logStore.updateLog(pendingLogId, {
        level: "error",
        message: "Failed to abort rebase.",
        details: errorMessage,
      });
    } finally {
      actionsStore.isActionLoading = false;
    }
  }

  return {
    isInConflict,
    conflictedFiles,
    enterConflictMode,
    exitConflictMode,
    handleContinue,
    handleAbort,
  };
});
