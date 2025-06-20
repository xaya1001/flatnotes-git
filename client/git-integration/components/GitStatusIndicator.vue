<template>
  <div
    class="fixed right-0 top-1/2 z-50 flex -translate-y-1/2 cursor-pointer items-center rounded-l-full bg-theme-background-elevated pr-3 shadow-lg transition-transform duration-300 hover:bg-theme-border"
    :class="{ 'translate-x-[-1px]': !panelUiStore.isSidebarVisible }"
    :style="{ transform: `translateX(-${sidebarVisibleWidth}px)` }"
    @click="$emit('toggle-sidebar')"
  >
    <!-- Toggle Icon -->
    <div class="p-2">
      <SvgIcon
        type="mdi"
        :path="
          panelUiStore.isSidebarVisible ? mdilChevronRight : mdilChevronLeft
        "
        :size="24"
        class="text-theme-text"
      />
    </div>

    <!-- Status Content (No more loading spinner here) -->
    <div
      v-if="!panelUiStore.isSidebarVisible"
      class="flex items-center space-x-3"
      :title="statusStore.tooltipText"
    >
      <!-- Base Info: Branch Icon and Name (Always Visible) -->
      <div class="flex items-center space-x-2 text-theme-text">
        <SvgIcon type="mdi" :path="mdilSitemap" :size="20" class="h-5 w-5" />
        <span class="text-sm font-semibold">{{ statusStore.branchName }}</span>
      </div>

      <!-- Dynamic Status Indicators -->
      <div class="flex items-center text-sm font-semibold">
        <!-- Error State -->
        <div
          v-if="statusStore.summaryError"
          class="flex items-center space-x-1 text-theme-danger"
        >
          <SvgIcon type="mdi" :path="mdilAlert" :size="20" />
          <span>Error</span>
        </div>

        <!-- Conflict State -->
        <div
          v-else-if="statusStore.repositoryState.includes('CONFLICT')"
          class="flex items-center space-x-1 text-theme-danger"
        >
          <SvgIcon type="mdi" :path="mdilAlertOctagon" :size="20" />
          <span>Conflict</span>
        </div>

        <!-- Behind State (Needs Pull) -->
        <div
          v-else-if="statusStore.commitsBehind > 0"
          class="flex items-center space-x-1 text-theme-text"
        >
          <SvgIcon type="mdi" :path="mdilArrowDown" :size="20" />
          <span>{{ statusStore.commitsBehind }}</span>
        </div>

        <!-- Ahead State (Needs Push) -->
        <div
          v-else-if="statusStore.commitsAhead > 0"
          class="flex items-center space-x-1 text-theme-text"
        >
          <SvgIcon type="mdi" :path="mdilArrowUp" :size="20" />
          <span>{{ statusStore.commitsAhead }}</span>
        </div>

        <!-- Changed State -->
        <div v-else-if="statusStore.filesChangedCount > 0">
          <span
            class="rounded-full bg-theme-brand px-2 py-0.5 text-xs font-bold text-white"
          >
            {{ statusStore.filesChangedCount }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useStatusStore } from "../stores/statusStore";
import { usePanelUiStore } from "../stores/panelUiStore";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdilSitemap,
  mdilAlert,
  mdilChevronLeft,
  mdilChevronRight,
  mdilArrowDown,
  mdilArrowUp,
  mdilAlertOctagon,
} from "@mdi/light-js";

defineEmits(["toggle-sidebar"]);

const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();

const sidebarVisibleWidth = computed(() => {
  return panelUiStore.isSidebarVisible ? panelUiStore.width : 0;
});
</script>
