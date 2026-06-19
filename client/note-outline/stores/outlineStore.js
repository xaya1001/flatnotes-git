import { computed, ref } from "vue";
import { defineStore } from "pinia";

export const useOutlineStore = defineStore("note-outline", () => {
  const headings = ref([]);
  const activeHeadingId = ref(null);
  const isSidebarVisible = ref(false);
  const isPinned = ref(false);
  const width = ref(480);

  const minLevel = computed(() => {
    if (headings.value.length === 0) return 1;
    return Math.min(...headings.value.map((heading) => heading.level));
  });

  function setHeadings(nextHeadings) {
    headings.value = nextHeadings;
    if (!activeHeadingId.value && nextHeadings.length > 0) {
      activeHeadingId.value = nextHeadings[0].id;
      return;
    }
    if (
      activeHeadingId.value &&
      !nextHeadings.some((heading) => heading.id === activeHeadingId.value)
    ) {
      activeHeadingId.value = nextHeadings[0]?.id || null;
    }
  }

  function setActiveHeading(id) {
    activeHeadingId.value = id;
  }

  function toggleSidebar() {
    isSidebarVisible.value = !isSidebarVisible.value;
  }

  function showSidebar() {
    isSidebarVisible.value = true;
  }

  function hideSidebar() {
    if (!isPinned.value) {
      isSidebarVisible.value = false;
    }
  }

  function forceHideSidebar() {
    isSidebarVisible.value = false;
  }

  function togglePin() {
    isPinned.value = !isPinned.value;
  }

  function reset() {
    headings.value = [];
    activeHeadingId.value = null;
    isSidebarVisible.value = false;
  }

  return {
    headings,
    activeHeadingId,
    isSidebarVisible,
    isPinned,
    width,
    minLevel,
    setHeadings,
    setActiveHeading,
    toggleSidebar,
    showSidebar,
    hideSidebar,
    forceHideSidebar,
    togglePin,
    reset,
  };
});
