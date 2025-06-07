<!-- client/components/GitStatusIndicator.vue -->
<template>
  <div 
    v-if="gitIntegrationEnabled && !error"
    class="fixed bottom-4 right-4 z-50 flex items-center p-2 rounded-full shadow-lg cursor-pointer bg-theme-background-elevated hover:bg-theme-border transition-colors duration-200"
    @click="$emit('toggle-panel')"
    :title="tooltipText"
  >
    <!-- Loading State -->
    <div v-if="isLoading" class="w-5 h-5 animate-spin text-theme-text-muted" role="status">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.75v1.5M17.125 6.875l-1.062 1.063M19.25 12h-1.5M17.125 17.125l-1.062-1.063M12 17.75v1.5M6.875 17.125l1.063-1.063M4.75 12h1.5M6.875 6.875l1.063 1.063"></path></svg>
      <span class="sr-only">Loading...</span>
    </div>
    
    <!-- Normal State -->
    <div v-else class="flex items-center space-x-2">
      <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-theme-text" viewBox="0 0 16 16" fill="currentColor"><path fill-rule="evenodd" d="M1.646 3.646a.5.5 0 01.708 0L4 5.293l1.646-1.647a.5.5 0 11.708.708L4.707 6l1.647 1.646a.5.5 0 01-.708.708L4 6.707l-1.646 1.647a.5.5 0 01-.708-.708L3.293 6 1.646 4.354a.5.5 0 010-.708zM6 3.5a.5.5 0 01.5.5v8a.5.5 0 01-1 0v-8a.5.5 0 01.5-.5zM12 3a.5.5 0 01.5.5v8a.5.5 0 01-1 0v-8A.5.5 0 0112 3z"></path></svg>
      <span class="text-sm font-semibold text-theme-text">{{ branchName }}</span>
      <span v-if="changesCount > 0" class="px-2 py-0.5 text-xs font-bold text-white bg-theme-brand rounded-full">
        {{ changesCount }}
      </span>
    </div>
  </div>
  <!-- Error State: Display nothing, but log to console -->
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useGlobalStore } from "../globalStore.js";
import { getGitStatusSummary } from '../api.js';

defineEmits(['toggle-panel']);

const globalStore = useGlobalStore();
const gitIntegrationEnabled = computed(() => globalStore.config.value?.flatnotesGitEnabled);

const isLoading = ref(true);
const error = ref(null);
const branchName = ref('');
const changesCount = ref(0);
let pollInterval = null;

const tooltipText = computed(() => {
  if (isLoading.value) return "Loading Git status...";
  if (error.value) return `Error: ${error.value}`;
  if (changesCount.value > 0) return `${changesCount.value} changes detected on branch '${branchName.value}'. Click to view.`;
  return `On branch '${branchName.value}'. Synced.`;
});

async function fetchStatus() {
  if (!gitIntegrationEnabled.value) return;
  try {
    const summary = await getGitStatusSummary();
    branchName.value = summary.current_branch || 'N/A';
    changesCount.value = summary.files_changed_count;
    error.value = null; // Clear previous errors on success
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to connect';
    console.error("GitStatusIndicator: Failed to fetch git status summary:", err);
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  if (gitIntegrationEnabled.value) {
    fetchStatus();
    pollInterval = setInterval(fetchStatus, 30000); // Poll every 30 seconds
  }
});

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval);
  }
});
</script>