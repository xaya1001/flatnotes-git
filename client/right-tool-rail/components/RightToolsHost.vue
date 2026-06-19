<template>
  <GitSidebar v-if="enabled" />
  <OutlineSidebar v-if="showOutlineTool" />
  <RightToolRail
    v-if="showRightToolRail"
    :active-panel-width="activeRightPanelWidth"
  >
    <GitStatusIndicator v-if="enabled" @toggle-sidebar="toggleGitSidebar" />
    <OutlineIndicator
      v-if="showOutlineTool"
      @toggle-sidebar="toggleOutlineSidebar"
    />
  </RightToolRail>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";

import GitSidebar from "../../git-integration/components/GitSidebar.vue";
import GitStatusIndicator from "../../git-integration/components/GitStatusIndicator.vue";
import { useGitIntegration } from "../../git-integration/composables/useGitIntegration.js";
import { usePanelUiStore } from "../../git-integration/stores/panelUiStore.js";
import OutlineIndicator from "../../note-outline/components/OutlineIndicator.vue";
import OutlineSidebar from "../../note-outline/components/OutlineSidebar.vue";
import { useNoteOutline } from "../../note-outline/composables/useNoteOutline.js";
import { useOutlineStore } from "../../note-outline/stores/outlineStore.js";
import RightToolRail from "./RightToolRail.vue";

const props = defineProps({
  enabled: {
    type: Boolean,
    default: false,
  },
});

const route = useRoute();
const gitPanelUiStore = usePanelUiStore();
const outlineStore = useOutlineStore();
const outlineEnabled = computed(() => props.enabled);

const showOutlineTool = computed(() => {
  return props.enabled && route.name === "note" && Boolean(route.params.title);
});
const showRightToolRail = computed(() => {
  return props.enabled;
});
const activeRightPanelWidth = computed(() => {
  if (gitPanelUiStore.isSidebarVisible) return gitPanelUiStore.width;
  if (outlineStore.isSidebarVisible) return outlineStore.width;
  return 0;
});

useGitIntegration();
useNoteOutline(route, outlineEnabled);

onMounted(() => {
  document.addEventListener("pointerdown", handleOutsidePointerDown, true);
});

onUnmounted(() => {
  document.removeEventListener("pointerdown", handleOutsidePointerDown, true);
});

function toggleGitSidebar() {
  if (gitPanelUiStore.isSidebarVisible) {
    return;
  }
  gitPanelUiStore.showSidebar();
  if (outlineStore.isSidebarVisible) {
    outlineStore.forceHideSidebar();
  }
}

function toggleOutlineSidebar() {
  if (outlineStore.isSidebarVisible) {
    return;
  }
  outlineStore.showSidebar();
  if (gitPanelUiStore.isSidebarVisible) {
    gitPanelUiStore.forceHideSidebar();
  }
}

function handleOutsidePointerDown(event) {
  if (!gitPanelUiStore.isSidebarVisible && !outlineStore.isSidebarVisible) {
    return;
  }

  const target = event.target;
  if (!(target instanceof Element)) return;
  if (
    target.closest("[data-right-tool-rail]") ||
    target.closest("[data-right-tool-sidebar]")
  ) {
    return;
  }

  gitPanelUiStore.hideSidebar();
  outlineStore.hideSidebar();
}
</script>
