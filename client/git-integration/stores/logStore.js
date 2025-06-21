// client/git-integration/stores/logStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import { useToast } from "primevue/usetoast";
import * as gitApi from "../gitApi";
import { usePanelUiStore } from "./panelUiStore";

/**
 * Manages the state for the Git activity log. It is populated by other stores
 * and can be refreshed manually.
 */
export const useLogStore = defineStore("git-log", () => {
  const toast = useToast();
  const panelUiStore = usePanelUiStore();

  // -- STATE --
  const logs = ref([]);

  // -- ACTIONS --
  /**
   * @param {object} logData
   * @param {'info'|'success'|'warn'|'error'} logData.level
   * @param {string} logData.message
   * @param {any} [logData.details]
   */
  function addLog(logData) {
    const newLog = {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      level: logData.level || "info",
      message: logData.message,
      details: logData.details || null,
      status: "completed",
    };
    logs.value.unshift(newLog);
    return newLog.id;
  }

  function addPendingLog(message) {
    const newLog = {
      id: uuidv4(),
      timestamp: new Date().toISOString(),
      level: "info",
      message: message,
      details: "Executing...",
      status: "pending",
    };
    logs.value.unshift(newLog);
    return newLog.id;
  }

  function updateLog(id, updateData) {
    const logIndex = logs.value.findIndex((log) => log.id === id);
    if (logIndex !== -1) {
      const updatedLog = { ...logs.value[logIndex], ...updateData };
      updatedLog.status = "completed";
      logs.value[logIndex] = updatedLog;
    }
  }

  async function fetchActivityLog() {
    try {
      const backendLogs = await gitApi.getGitActivityLog();
      // Replace the current log state with the latest from the server.
      logs.value = backendLogs.map((log) => ({ ...log, status: "completed" }));
    } catch (error) {
      console.error("Failed to fetch activity log from backend:", error);
      addLog({
        level: "error",
        message: "Failed to fetch activity logs.",
        details: error.message,
      });
    }
  }

  async function clearAllLogs() {
    const confirmed = await panelUiStore.showConfirmation({
      title: "Confirm Clear Log",
      message:
        "This will permanently delete all activity log entries from the server. This cannot be undone.",
      confirmButtonText: "Yes, Clear Log",
      confirmButtonStyle: "danger",
    });

    if (confirmed) {
      try {
        await gitApi.clearGitActivityLog();
        logs.value = []; // Clear local state immediately
        toast.add({
          severity: "success",
          summary: "Success",
          detail: "Activity log cleared.",
          life: 3000,
        });
      } catch (err) {
        toast.add({
          severity: "error",
          summary: "Error",
          detail: "Failed to clear activity log.",
          life: 5000,
        });
      }
    }
  }

  function initialize() {
    // Fetch initial logs when the application loads.
    fetchActivityLog();
  }

  function cleanup() {
    // No-op. There are no connections or intervals to clear.
  }

  return {
    logs,
    addLog,
    addPendingLog,
    updateLog,
    initialize,
    cleanup,
    fetchActivityLog,
    clearAllLogs,
  };
});
