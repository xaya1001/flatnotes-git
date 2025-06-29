<template>
  <div ref="viewerElement"></div>
</template>

<script setup>
import Viewer from "@toast-ui/editor/dist/toastui-editor-viewer";
import { onMounted, onUnmounted, ref, nextTick } from "vue";

import eventBus from "../../git-integration/services/eventBus.js";
import baseOptions from "./baseOptions.js";
import extendedAutolinks from "./extendedAutolinks.js";
import {
  renderMermaidBlocks,
  reinitializeMermaidTheme,
} from "./mermaidRenderer.js";

const props = defineProps({
  initialValue: String,
});

const viewerElement = ref();

// Overall Comment: Theme change handler is now more performant.
const handleThemeChange = () => {
  if (viewerElement.value) {
    const newTheme = document.body.classList.contains("dark")
      ? "dark"
      : "default";
    reinitializeMermaidTheme(newTheme);
    renderMermaidBlocks(viewerElement.value);
  }
};

onMounted(() => {
  // Set initial theme before creating the viewer
  const initialTheme = document.body.classList.contains("dark")
    ? "dark"
    : "default";
  reinitializeMermaidTheme(initialTheme);

  new Viewer({
    ...baseOptions,
    extendedAutolinks,
    el: viewerElement.value,
    initialValue: props.initialValue,
  });

  // Overall Comment: Replaced setTimeout with nextTick for reliability.
  nextTick(() => {
    if (viewerElement.value) {
      renderMermaidBlocks(viewerElement.value);
    }
  });

  eventBus.on("theme-changed", handleThemeChange);
});

// Overall Comment: Unsubscribe from eventBus to prevent memory leaks.
onUnmounted(() => {
  eventBus.off("theme-changed", handleThemeChange);
});
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor-viewer.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
