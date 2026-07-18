<template>
  <RightToolRailItem
    ref="indicatorElement"
    :active="panelUiStore.isSidebarVisible"
    :icon-path="mdiSourceBranch"
    :title="statusStore.tooltipText"
    @activate="$emit('toggle-sidebar')"
  >
    {{ statusStore.branchName || "Git" }}
    <template v-if="statusBadgeText" #badge>
      {{ statusBadgeText }}
    </template>
  </RightToolRailItem>
</template>

<script setup>
import { computed, ref } from "vue";
import { useStatusStore } from "../stores/statusStore";
import { usePanelUiStore } from "../stores/panelUiStore";
import RightToolRailItem from "../../right-tool-rail/components/RightToolRailItem.vue";
import { mdiSourceBranch } from "@mdi/js";

defineEmits(["toggle-sidebar"]);

const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();
const indicatorElement = ref(null);

const statusBadgeText = computed(() => {
  if (statusStore.summaryError) return "!";
  if (statusStore.repositoryState.includes("CONFLICT")) return "!";
  if (statusStore.commitsBehind > 0) return String(statusStore.commitsBehind);
  if (statusStore.commitsAhead > 0) return String(statusStore.commitsAhead);
  if (statusStore.filesChangedCount > 0) {
    return String(statusStore.filesChangedCount);
  }
  return "";
});

defineExpose({ element: indicatorElement });
</script>
