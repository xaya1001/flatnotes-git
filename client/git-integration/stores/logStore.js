// client/git-integration/stores/logStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import * as gitApi from "../gitApi";

/**
 * Manages the state for the Git activity log, including polling for
 * new logs from the backend.
 */
export const useLogStore = defineStore("git-log", () => {
  // -- STATE --
  const logs = ref([]);
  let logPollInterval = null;

  // -- ACTIONS --
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
      const existingIds = new Set(logs.value.map((log) => log.id));
      const newLogs = backendLogs.filter((log) => !existingIds.has(log.id));

      if (newLogs.length > 0) {
        const formattedNewLogs = newLogs.map((log) => ({
          ...log,
          status: "completed",
        }));
        logs.value.push(...formattedNewLogs);
        logs.value.sort(
          (a, b) => new Date(b.timestamp) - new Date(a.timestamp),
        );
      }
    } catch (error) {
      console.error("Failed to fetch activity log from backend:", error);
    }
  }

  function initialize() {
    fetchActivityLog();
    logPollInterval = setInterval(fetchActivityLog, 10000);
  }

  function cleanup() {
    if (logPollInterval) clearInterval(logPollInterval);
  }

  return {
    logs,
    addLog,
    addPendingLog,
    updateLog,
    initialize,
    cleanup,
    fetchActivityLog,
  };
});
