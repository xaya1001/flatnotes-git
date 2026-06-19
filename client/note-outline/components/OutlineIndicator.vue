<template>
  <RightToolRailItem
    :active="outlineStore.isSidebarVisible"
    :icon-path="mdiFormatListBulleted"
    :title="tooltipText"
    @activate="$emit('toggle-sidebar')"
  >
    Outline
  </RightToolRailItem>
</template>

<script setup>
import { computed } from "vue";
import { mdiFormatListBulleted } from "@mdi/js";

import RightToolRailItem from "../../right-tool-rail/components/RightToolRailItem.vue";
import { useOutlineStore } from "../stores/outlineStore.js";

defineEmits(["toggle-sidebar"]);

const outlineStore = useOutlineStore();

const tooltipText = computed(() => {
  if (outlineStore.headings.length === 0) {
    return "No headings in this note.";
  }
  return `Outline: ${outlineStore.headings.length} headings.`;
});
</script>
