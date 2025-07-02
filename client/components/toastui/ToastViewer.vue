<template>
  <div ref="viewerElement"></div>
</template>

<script setup>
import Viewer from "@toast-ui/editor/dist/toastui-editor-viewer";
import { onMounted, ref, nextTick, watch, onUnmounted } from "vue";
import baseOptions from "./baseOptions.js";
import extendedAutolinks from "./extendedAutolinks.js";
import {
  renderMermaidBlocks,
  cleanupMermaidRenders,
} from "./mermaidRenderer.js";

const props = defineProps({
  initialValue: String,
});

const viewerElement = ref();
let viewerInstance;

const destroyViewer = () => {
  if (viewerElement.value) {
    cleanupMermaidRenders(viewerElement.value);
  }
  if (viewerInstance) {
    viewerInstance.destroy();
    viewerInstance = null;
  }
};

const createViewer = () => {
  if (!viewerElement.value) return;

  viewerInstance = new Viewer({
    ...baseOptions,
    extendedAutolinks,
    el: viewerElement.value,
    initialValue: props.initialValue,
  });

  nextTick(() => {
    if (viewerElement.value) {
      renderMermaidBlocks(viewerElement.value);
    }
  });
};

onMounted(createViewer);

// FINAL FIX: Always destroy and recreate the viewer on content change to prevent state leaks.
watch(
  () => props.initialValue,
  () => {
    destroyViewer();
    createViewer();
  },
);

onUnmounted(destroyViewer);
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor-viewer.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
