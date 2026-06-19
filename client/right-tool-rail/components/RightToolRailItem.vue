<template>
  <button
    ref="itemElement"
    type="button"
    class="relative flex h-11 w-32 cursor-pointer items-center rounded-l-full bg-theme-background-elevated pl-3 pr-4 text-theme-text shadow-lg transition-colors duration-200 hover:bg-theme-border focus:outline-none"
    :class="{ 'bg-theme-border': active }"
    :title="title"
    :aria-pressed="active"
    @click="$emit('activate')"
  >
    <div class="shrink-0">
      <SvgIcon type="mdi" :path="iconPath" :size="22" class="h-5 w-5" />
    </div>
    <div
      v-if="$slots.default"
      class="ml-2 min-w-0 truncate text-sm font-semibold"
    >
      <slot />
    </div>
    <div
      v-if="$slots.badge"
      class="absolute -left-1 -top-1 flex min-h-4 min-w-4 items-center justify-center rounded-full bg-theme-brand px-1 text-[10px] font-semibold leading-4 text-theme-background"
    >
      <slot name="badge" />
    </div>
  </button>
</template>

<script setup>
import { ref } from "vue";
import SvgIcon from "@jamescoyle/vue-icon";

defineProps({
  active: {
    type: Boolean,
    default: false,
  },
  iconPath: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    default: "",
  },
});

defineEmits(["activate"]);

const itemElement = ref(null);

defineExpose({ element: itemElement });
</script>
