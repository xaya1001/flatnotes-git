// client/git-integration/stores/logStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import { useToast } from "primevue/usetoast";
import * as gitApi from "../gitApi";
import eventBus from "../eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";

export const useLogStore = defineStore("git-log", () => {
  const toast = useToast();

  const logs = ref([]);
  const operationIdToLogIdMap = ref({});

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
    try {
      await gitApi.clearGitActivityLog();
      await fetchActivityLog();
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

  // --- Event Listeners ---
  eventBus.on(GIT_OPERATION.WILL_START, (payload) => {
    const logId = addPendingLog(payload.actionName);
    operationIdToLogIdMap.value[payload.operationId] = logId;
  });

  eventBus.on(GIT_OPERATION.DID_SUCCEED, (payload) => {
    const logId = operationIdToLogIdMap.value[payload.operationId];
    if (logId) {
      const successMessage = `${payload.actionName} successful.`;
      updateLog(logId, {
        level: "success",
        message: successMessage,
        details: payload.response.details || null,
      });
      delete operationIdToLogIdMap.value[payload.operationId];

      // Show toast for user-facing actions
      toast.add({
        severity: "success",
        summary: "Success",
        detail: successMessage,
        life: 3000,
      });
    }
  });

  eventBus.on(GIT_OPERATION.DID_FAIL, (payload) => {
    const logId = operationIdToLogIdMap.value[payload.operationId];
    if (logId) {
      const errorData = payload.err.response?.data?.detail;
      const errorMessage =
        errorData?.message || errorData || payload.err.message;
      updateLog(logId, {
        level: "error",
        message: `Failed: ${payload.actionName}`,
        details: errorMessage,
      });
      delete operationIdToLogIdMap.value[payload.operationId];

      toast.add({
        severity: "error",
        summary: `Error: ${payload.actionName}`,
        detail: errorMessage,
        life: 5000,
      });
    }
  });

  eventBus.on(GIT_CONFLICT.DETECTED, (payload) => {
    const logId = operationIdToLogIdMap.value[payload.operationId];
    if (logId) {
      const { state, conflicted_files } = payload.errorData;
      const conflictType = state.includes("REBASING") ? "Rebase" : "Merge";
      updateLog(logId, {
        level: "warn",
        message: `Sync failed: ${conflictType} Conflict.`,
        details: `Files with conflicts: ${conflicted_files.join(", ")}`,
      });
      delete operationIdToLogIdMap.value[payload.operationId];
    }
  });

  eventBus.on(GIT_CONFLICT.RESOLVED, (payload) => {
    const logId = operationIdToLogIdMap.value[payload.operationId];
    if (logId) {
      const message = `${payload.actionName} successful.`;
      updateLog(logId, {
        level: "success",
        message: message,
        details: payload.response.details || payload.response.stdout,
      });
      delete operationIdToLogIdMap.value[payload.operationId];

      toast.add({
        severity: "success",
        summary: "Operation Complete",
        detail: payload.response.message,
        life: 4000,
      });
    }
  });

  function initialize() {
    fetchActivityLog();
  }

  function cleanup() {
    // No-op.
  }

  return {
    logs,
    addLog,
    initialize,
    cleanup,
    fetchActivityLog,
    clearAllLogs,
  };
});
