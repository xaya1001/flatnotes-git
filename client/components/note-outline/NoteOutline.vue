<template>
  <div v-if="hasHeadings" class="print:hidden">
    <aside
      v-show="isVisible"
      class="fixed left-0 top-0 z-30 flex h-full w-72 flex-col border-r border-theme-border bg-theme-background-elevated shadow-lg transition-transform duration-300"
      :class="{ '-translate-x-full': !isVisible }"
      aria-label="Note outline"
    >
      <div
        class="flex flex-shrink-0 items-center justify-between border-b border-theme-border p-3"
      >
        <div class="flex items-center space-x-2 text-theme-text">
          <SvgIcon type="mdi" :path="mdilFormatListBulleted" :size="20" />
          <h2 class="text-sm font-semibold">On this note</h2>
        </div>
        <button
          @click="toggleVisible"
          class="rounded-full p-1 text-theme-text-muted hover:bg-theme-border hover:text-theme-text"
          title="Collapse outline"
          aria-label="Collapse outline"
        >
          <SvgIcon type="mdi" :path="mdilChevronLeft" :size="20" />
        </button>
      </div>

      <nav class="min-h-0 flex-grow overflow-y-auto p-2" aria-label="Headings">
        <button
          v-for="heading in headings"
          :key="heading.id"
          type="button"
          class="block w-full truncate rounded border-l-2 py-1.5 pr-2 text-left text-xs transition-colors"
          :class="[
            heading.id === activeId
              ? 'border-theme-brand bg-theme-background text-theme-brand'
              : 'border-transparent text-theme-text-muted hover:bg-theme-background hover:text-theme-text',
          ]"
          :style="{
            paddingLeft: `${Math.max(0, heading.level - 1) * 0.75 + 0.5}rem`,
          }"
          :title="heading.text"
          @click="navigateToHeading(heading)"
        >
          {{ heading.text }}
        </button>
      </nav>
    </aside>

    <button
      type="button"
      class="fixed left-0 top-1/2 z-40 flex -translate-y-1/2 items-center rounded-r-full bg-theme-background-elevated py-2 pl-2 pr-3 text-theme-text shadow-lg transition-transform duration-300 hover:bg-theme-border"
      :style="{ transform: toggleTransform }"
      :title="isVisible ? 'Collapse outline' : 'Expand outline'"
      :aria-label="isVisible ? 'Collapse outline' : 'Expand outline'"
      @click="toggleVisible"
    >
      <SvgIcon
        type="mdi"
        :path="isVisible ? mdilChevronLeft : mdilChevronRight"
        :size="24"
      />
      <div v-if="!isVisible" class="ml-1 flex items-center space-x-2">
        <SvgIcon type="mdi" :path="mdilFormatListBulleted" :size="18" />
        <span class="text-sm font-semibold">Outline</span>
      </div>
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdilChevronLeft,
  mdilChevronRight,
  mdilFormatListBulleted,
} from "@mdi/light-js";

const STORAGE_KEY = "noteOutlineVisible";
const MIN_EXPANDED_WIDTH = 1280;
const PANEL_WIDTH = 288;

const props = defineProps({
  headings: { type: Array, default: () => [] },
  activeId: { type: String, default: "" },
  minHeadings: { type: Number, default: 2 },
});

const emit = defineEmits(["navigate"]);

const isVisible = ref(false);
const hasUserPreference = ref(false);

const hasHeadings = computed(() => props.headings.length >= props.minHeadings);
const toggleTransform = computed(() =>
  isVisible.value
    ? `translateX(${PANEL_WIDTH}px) translateY(-50%)`
    : "translateX(0) translateY(-50%)",
);

function readStoredPreference() {
  const storedValue = localStorage.getItem(STORAGE_KEY);
  if (storedValue === null) return null;
  return storedValue === "true";
}

function applyResponsiveVisibility() {
  const storedPreference = readStoredPreference();
  hasUserPreference.value = storedPreference !== null;

  if (!hasHeadings.value) {
    isVisible.value = false;
    return;
  }

  if (window.innerWidth < MIN_EXPANDED_WIDTH) {
    isVisible.value = false;
    return;
  }

  isVisible.value = storedPreference ?? true;
}

function toggleVisible() {
  isVisible.value = !isVisible.value;
  hasUserPreference.value = true;
  localStorage.setItem(STORAGE_KEY, String(isVisible.value));
}

function navigateToHeading(heading) {
  emit("navigate", heading);
}

function handleResize() {
  if (window.innerWidth < MIN_EXPANDED_WIDTH) {
    isVisible.value = false;
    return;
  }

  if (!hasUserPreference.value && hasHeadings.value) {
    isVisible.value = true;
  }
}

watch(hasHeadings, applyResponsiveVisibility, { immediate: true });

onMounted(() => {
  window.addEventListener("resize", handleResize);
  applyResponsiveVisibility();
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
});
</script>
