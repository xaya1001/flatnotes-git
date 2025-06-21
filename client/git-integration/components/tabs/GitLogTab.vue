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
        @click="logStore.clearAllLogs"
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
import { getLogLevelBgClass, getLogLevelTextColorClass } from "../../gitUtils";
import LogDetail from "../shared/LogDetail.vue";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdiDeleteSweep } from "@mdi/js";

const logStore = useLogStore();

const activeLogLevelFilter = ref("all");
const logLevelOptions = ref([
  { name: "All", value: "all" },
  { name: "Success", value: "success" },
  { name: "Error", value: "error" },
  { name: "Info", value: "info" },
  { name: "Warn", value: "warn" },
]);

const filteredLogs = computed(() => {
  if (activeLogLevelFilter.value === "all") {
    return logStore.logs;
  }
  return logStore.logs.filter(
    (log) => log.level === activeLogLevelFilter.value,
  );
});

function setLogLevelFilter(level) {
  activeLogLevelFilter.value = level;
}
</script>
