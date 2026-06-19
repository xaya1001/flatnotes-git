<template>
  <div
    data-right-tool-rail
    class="fixed right-0 top-1/2 z-50 flex -translate-y-1/2 flex-col items-end gap-2 transition-transform duration-300 print:hidden"
    :style="{
      transform: `translateX(-${activePanelWidth}px) translateY(-50%)`,
    }"
  >
    <slot />
  </div>
</template>

<script setup>
defineProps({
  activePanelWidth: {
    type: Number,
    default: 0,
  },
});
</script>
