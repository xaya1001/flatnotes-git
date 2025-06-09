<!-- client/components/GitStatusIndicator.vue -->
<template>
  <div
    v-if="gitIntegrationEnabled"
    class="fixed right-5 top-5 z-50 flex cursor-pointer items-center rounded-full p-2 shadow-lg transition-colors duration-200"
    :class="{
      'bg-theme-background-elevated hover:bg-theme-border': !store.summaryError,
      'bg-red-100 text-theme-danger dark:bg-red-900/50': store.summaryError,
    }"
    @click="$emit('toggle-panel')"
    :title="store.tooltipText"
  >
    <!-- Error State -->
    <div v-if="store.summaryError" class="flex items-center space-x-2">
      <SvgIcon type="mdi" :path="mdilAlert" :size="20" class="h-5 w-5" />
      <span class="text-sm font-semibold">Error</span>
    </div>

    <!-- Loading State -->
    <div
      v-else-if="store.isLoadingSummary"
      class="h-5 w-5 animate-spin text-theme-text-muted"
      role="status"
    >
      <SvgIcon type="mdi" :path="mdilRefresh" :size="20" />
    </div>

    <!-- Normal State -->
    <div v-else class="flex items-center space-x-2 text-theme-text">
      <SvgIcon type="mdi" :path="mdilSitemap" :size="20" class="h-5 w-5" />
      <span class="text-sm font-semibold">{{ store.branchName }}</span>
      <span
        v-if="store.filesChangedCount > 0"
        class="rounded-full bg-theme-brand px-2 py-0.5 text-xs font-bold text-white"
      >
        {{ store.filesChangedCount }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useGlobalStore } from "../globalStore";
import { useGitStore } from "../gitStore";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilSitemap, mdilRefresh, mdilAlert } from "@mdi/light-js";

defineEmits(["toggle-panel"]);

const globalStore = useGlobalStore();
const store = useGitStore();

const gitIntegrationEnabled = computed(
  () => globalStore.config.value?.flatnotesGitEnabled,
);
</script>
