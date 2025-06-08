<!-- client/components/GitStatusIndicator.vue -->
<template>
  <div
    v-if="gitIntegrationEnabled && !error"
    class="fixed right-5 top-5 z-50 flex cursor-pointer items-center rounded-full bg-theme-background-elevated p-2 shadow-lg transition-colors duration-200 hover:bg-theme-border"
    @click="$emit('toggle-panel')"
    :title="tooltipText"
  >
    <!-- Loading State -->
    <div
      v-if="isLoading"
      class="h-5 w-5 animate-spin text-theme-text-muted"
      role="status"
    >
      <SvgIcon type="mdi" :path="mdilRefresh" />
    </div>

    <!-- Normal State -->
    <div v-else class="flex items-center space-x-2">
      <SvgIcon type="mdi" :path="mdilSitemap" class="h-5 w-5 text-theme-text" />
      <span class="text-sm font-semibold text-theme-text">{{
        branchName
      }}</span>
      <span
        v-if="changesCount > 0"
        class="rounded-full bg-theme-brand px-2 py-0.5 text-xs font-bold text-white"
      >
        {{ changesCount }}
      </span>
    </div>
  </div>
  <!-- Error State: Display nothing, but log to console -->
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useGlobalStore } from '../globalStore.js';
import { getGitStatusSummary } from '../api.js';
import SvgIcon from '@jamescoyle/vue-icon';
import { mdilSitemap, mdilRefresh } from '@mdi/light-js';

defineEmits(['toggle-panel']);

const globalStore = useGlobalStore();
const gitIntegrationEnabled = computed(
  () => globalStore.config.value?.flatnotesGitEnabled
);

const isLoading = ref(true);
const error = ref(null);
const branchName = ref('');
const changesCount = ref(0);
let pollInterval = null;

const tooltipText = computed(() => {
  if (isLoading.value) return 'Loading Git status...';
  if (error.value) return `Error: ${error.value}`;
  if (changesCount.value > 0)
    return `${changesCount.value} changes detected on branch '${branchName.value}'. Click to view.`;
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
    console.error(
      'GitStatusIndicator: Failed to fetch git status summary:',
      err
    );
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
