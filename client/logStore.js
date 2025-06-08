// client/logStore.js

import { defineStore } from 'pinia';
import { ref } from 'vue';
import { v4 as uuidv4 } from 'uuid';

export const useLogStore = defineStore('git-log', () => {
  const logs = ref([]);

  /**
   * Adds a new log entry, typically for immediate feedback.
   * Returns the ID of the newly created log entry.
   * @param {object} logData - { level, message, details }
   * @returns {string} The ID of the log entry.
   */
  function addLog(logData) {
    const id = uuidv4();
    const newLog = {
      id,
      timestamp: new Date().toISOString(),
      level: logData.level || 'info',
      message: logData.message,
      details: logData.details || null,
      status: 'completed' // 'pending' or 'completed'
    };
    logs.value.unshift(newLog);
    return id;
  }

  /**
   * Adds a pending log entry and returns its ID for future updates.
   * @param {string} message - The initial message for the pending action.
   * @returns {string} The ID of the pending log entry.
   */
  function addPendingLog(message) {
    const id = uuidv4();
    const newLog = {
      id,
      timestamp: new Date().toISOString(),
      level: 'info',
      message: message,
      details: 'Executing...',
      status: 'pending'
    };
    logs.value.unshift(newLog);
    return id;
  }

  /**
   * Updates an existing log entry, usually a pending one.
   * @param {string} id - The ID of the log to update.
   * @param {object} updateData - { level, message, details, status }
   */
  function updateLog(id, updateData) {
    const logIndex = logs.value.findIndex((log) => log.id === id);
    if (logIndex !== -1) {
      const updatedLog = { ...logs.value[logIndex], ...updateData };
      updatedLog.status = 'completed'; // Mark as completed
      logs.value[logIndex] = updatedLog;
    }
  }

  /**
   * Merges logs fetched from the backend, avoiding duplicates.
   * @param {Array} backendLogs - Logs from the /api/git/activity-log endpoint.
   */
  function mergeBackendLogs(backendLogs) {
    const existingIds = new Set(logs.value.map((log) => log.id));
    const newLogs = backendLogs.filter((log) => !existingIds.has(log.id));

    if (newLogs.length > 0) {
      // Add a 'completed' status to backend logs for consistency
      const formattedNewLogs = newLogs.map((log) => ({
        ...log,
        status: 'completed'
      }));
      logs.value.push(...formattedNewLogs);
      // Sort all logs by timestamp descending (newest first)
      logs.value.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }
  }

  return { logs, addLog, addPendingLog, updateLog, mergeBackendLogs };
});
