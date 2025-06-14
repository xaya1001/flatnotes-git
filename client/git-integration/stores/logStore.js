// client/git-integration/stores/logStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import * as gitApi from "../gitApi";
import { connectToGitEvents } from "../eventSource";

/**
 * Manages the state for the Git activity log, including listening for
 * real-time updates from the backend.
 */
export const useLogStore = defineStore("git-log", () => {
  // -- STATE --
  const logs = ref([]);

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
    // This can still be called manually (e.g., refresh button)
    try {
      const backendLogs = await gitApi.getGitActivityLog();
      logs.value = backendLogs.map((log) => ({ ...log, status: "completed" }));
    } catch (error) {
      console.error("Failed to fetch activity log from backend:", error);
    }
  }

  function initialize() {
    // Fetch initial logs once
    fetchActivityLog();

    // Subscribe to real-time updates
    const eventSource = connectToGitEvents();
    eventSource.addEventListener("log_update", (event) => {
      const backendLogs = JSON.parse(event.data);
      // Replace the entire log state with the latest from the server
      logs.value = backendLogs.map((log) => ({ ...log, status: "completed" }));
    });
  }

  function cleanup() {
    // Connection is managed globally.
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
