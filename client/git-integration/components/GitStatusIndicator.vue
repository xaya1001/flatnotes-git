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

    <!-- Status Content -->
    <div
      v-if="!panelUiStore.isSidebarVisible"
      class="flex items-center space-x-2"
      :title="statusStore.tooltipText"
    >
      <div v-if="statusStore.summaryError" class="flex items-center space-x-2">
        <SvgIcon
          type="mdi"
          :path="mdilAlert"
          :size="20"
          class="h-5 w-5 text-theme-danger"
        />
        <span class="text-sm font-semibold text-theme-danger">Error</span>
      </div>
      <div
        v-else-if="statusStore.isLoadingSummary"
        class="h-5 w-5 animate-spin text-theme-text-muted"
        role="status"
      >
        <SvgIcon type="mdi" :path="mdilRefresh" :size="20" />
      </div>
      <div v-else class="flex items-center space-x-2 text-theme-text">
        <SvgIcon type="mdi" :path="mdilSitemap" :size="20" class="h-5 w-5" />
        <span class="text-sm font-semibold">{{ statusStore.branchName }}</span>
        <span
          v-if="statusStore.filesChangedCount > 0"
          class="rounded-full bg-theme-brand px-2 py-0.5 text-xs font-bold text-white"
        >
          {{ statusStore.filesChangedCount }}
        </span>
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
  mdilRefresh,
  mdilAlert,
  mdilChevronLeft,
  mdilChevronRight,
} from "@mdi/light-js";

defineEmits(["toggle-sidebar"]);

const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();

const sidebarVisibleWidth = computed(() => {
  return panelUiStore.isSidebarVisible ? panelUiStore.width : 0;
});
</script>
