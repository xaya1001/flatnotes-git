<!-- client/git-integration/components/tabs/GitLogTab.vue -->
<template>
  <div class="flex h-full flex-col p-2">
    <!-- Filter and Action Area -->
    <div class="mb-2 flex flex-shrink-0 items-center justify-between">
      <div class="flex items-center space-x-2">
        <button
          v-for="filter in logLevelOptions"
          :key="filter.value"
          @click="setLogLevelFilter(filter.value)"
          class="rounded-full px-3 py-1 text-xs font-semibold transition-colors duration-200"
          :class="[
            activeLogLevelFilter === filter.value
              ? 'text-white'
              : getLogLevelTextColorClass(filter.value),
            activeLogLevelFilter === filter.value
              ? getLogLevelBgClass(filter.value)
              : 'bg-theme-background hover:bg-theme-border',
          ]"
        >
          {{ filter.name }}
        </button>
      </div>
      <button
        @click="handleClearLogs"
        :disabled="logStore.logs.length === 0"
        class="flex items-center space-x-1 rounded-full bg-theme-background px-3 py-1 text-xs font-semibold text-theme-text-muted transition-colors duration-200 hover:bg-theme-border hover:text-theme-danger disabled:cursor-not-allowed disabled:opacity-50"
        title="Clear all log entries"
      >
        <SvgIcon type="mdi" :path="mdiDeleteSweep" :size="14" />
        <span>Clear Log</span>
      </button>
    </div>
    <!-- Scrollable Log Area -->
    <div class="min-h-0 flex-grow overflow-y-auto">
      <div v-if="filteredLogs.length > 0">
        <div
          v-for="log in filteredLogs"
          :key="log.id"
          class="border-b border-theme-border p-2 last:border-b-0"
        >
          <div class="flex items-center">
            <span
              class="mr-2 h-3 w-3 flex-shrink-0 rounded-full"
              :class="getLogLevelBgClass(log.level)"
            ></span>
            <span class="mr-2 text-sm font-semibold">{{ log.message }}</span>
            <span class="ml-auto text-xs text-theme-text-muted">{{
              new Date(log.timestamp).toLocaleTimeString()
            }}</span>
          </div>
          <LogDetail v-if="log.details" :details="log.details" />
        </div>
      </div>
      <p v-else class="py-4 text-center text-sm text-theme-text-muted">
        No logs to display for this level.
      </p>
    </div>
  </div>
</template>
<script setup>
import { ref, computed } from "vue";
import { useLogStore } from "../../stores/logStore";
import { usePanelUiStore } from "../../stores/panelUiStore";
import { getLogLevelBgClass, getLogLevelTextColorClass } from "../../gitUtils";
import LogDetail from "../shared/LogDetail.vue";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiDeleteSweep } from "@mdi/js";

const logStore = useLogStore();
const panelUiStore = usePanelUiStore();

const activeLogLevelFilter = ref("all");
const logLevelOptions = ref([
  { name: "All", value: "all" },
  { name: "Success", value: "success" },
  { name: "Error", value: "error" },
  { name: "Info", value: "info" },
  { name: "Warn", value: "warn" },
]);

const condensedLogs = computed(() => {
  if (logStore.logs.length === 0) return [];

  const result = [];
  let lastLog = null;
  let consecutiveCount = 0;

  for (const log of logStore.logs) {
    // Check for consecutive, identical, successful auto-sync logs
    if (
      lastLog &&
      log.id === "auto-fetch-task" &&
      lastLog.id === "auto-fetch-task" &&
      log.level === "success" &&
      lastLog.level === "success"
    ) {
      consecutiveCount++;
    } else {
      if (lastLog && consecutiveCount > 0) {
        // Update the last log's message before moving on
        const lastPushed = result[result.length - 1];
        lastPushed.message = `${lastPushed.message} (x${consecutiveCount + 1})`;
      }
      result.push({ ...log }); // Push a copy
      consecutiveCount = 0;
    }
    lastLog = log;
  }

  // Handle the very last log if it was part of a sequence
  if (lastLog && consecutiveCount > 0) {
    const lastPushed = result[result.length - 1];
    lastPushed.message = `${lastPushed.message} (x${consecutiveCount + 1})`;
  }

  return result;
});

const filteredLogs = computed(() => {
  const logsToFilter = condensedLogs.value; // Use the condensed logs
  if (activeLogLevelFilter.value === "all") {
    return logsToFilter;
  }
  return logsToFilter.filter((log) => log.level === activeLogLevelFilter.value);
});

function setLogLevelFilter(level) {
  activeLogLevelFilter.value = level;
}

async function handleClearLogs() {
  const confirmed = await panelUiStore.showConfirmation({
    title: "Confirm Clear Log",
    message:
      "This will permanently delete all activity log entries from the server. This cannot be undone.",
    confirmButtonText: "Yes, Clear Log",
    confirmButtonStyle: "danger",
  });

  if (confirmed) {
    await logStore.clearAllLogs();
  }
}
</script>
