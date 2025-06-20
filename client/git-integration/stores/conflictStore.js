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

  function enterConflictMode(errorData, options = {}) {
    isInConflict.value = true;
    conflictedFiles.value = errorData.conflicted_files;

    const conflictType = errorData.state.includes("REBASING")
      ? "Rebase"
      : "Merge";

    if (!options.silent) {
      toast.add({
        severity: "warn",
        summary: `Sync Conflict: ${conflictType}`,
        detail: "Please resolve the file conflicts to continue.",
        life: 6000,
      });
    }

    logStore.addLog({
      level: "warn",
      message: `${conflictType} conflict detected.`,
      details: `Files with conflicts: ${errorData.conflicted_files.join(", ")}`,
    });
  }

  function exitConflictMode() {
    isInConflict.value = false;
    conflictedFiles.value = [];
  }

  async function handleContinue() {
    const actionsStore = useActionsStore();
    actionsStore.isActionLoading = true;
    const pendingLogId = logStore.addPendingLog("Finalizing operation...");
    try {
      const response = await gitApi.gitConflictContinue();
      toast.add({
        severity: "success",
        summary: "Operation Complete",
        detail: response.message,
        life: 4000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: "Operation finished successfully.",
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
      const errorData = err.response?.data?.detail;
      if (err.response?.status === 409 && errorData?.state) {
        enterConflictMode(errorData); // Re-enter conflict mode with new data
        logStore.updateLog(pendingLogId, {
          level: "warn",
          message: "Operation paused with new conflicts.",
          details: errorData.message,
        });
      } else {
        const errorMessage = errorData?.message || errorData || err.message;
        toast.add({
          severity: "error",
          summary: "Operation Failed",
          detail: errorMessage,
          life: 5000,
        });
        logStore.updateLog(pendingLogId, {
          level: "error",
          message: "Failed to continue operation.",
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
    const pendingLogId = logStore.addPendingLog("Aborting operation...");
    try {
      const response = await gitApi.gitConflictAbort();
      toast.add({
        severity: "info",
        summary: "Operation Aborted",
        detail:
          response.message ||
          "The repository has been returned to a previous state.",
        life: 4000,
      });
      logStore.updateLog(pendingLogId, {
        level: "warn",
        message: "Operation aborted by user.",
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
        message: "Failed to abort operation.",
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
