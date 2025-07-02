<template>
  <div ref="viewerElement"></div>
</template>

<script setup>
import Viewer from "@toast-ui/editor/dist/toastui-editor-viewer";
import { onMounted, ref, nextTick, watch, onUnmounted } from "vue";
import baseOptions from "./baseOptions.js";
import extendedAutolinks from "./extendedAutolinks.js";
import { renderMermaidBlocks } from "./mermaidRenderer.js";

const props = defineProps({
  initialValue: String,
});

const viewerElement = ref();
let viewerInstance;

const createOrUpdateViewer = () => {
  if (!viewerElement.value) return;

  if (viewerInstance) {
    viewerInstance.setMarkdown(props.initialValue || "");
  } else {
    viewerInstance = new Viewer({
      ...baseOptions,
      extendedAutolinks,
      el: viewerElement.value,
      initialValue: props.initialValue,
    });
  }
  nextTick(() => {
    if (viewerElement.value) {
      renderMermaidBlocks(viewerElement.value);
    }
  });
};

onMounted(createOrUpdateViewer);

watch(() => props.initialValue, createOrUpdateViewer);

onUnmounted(() => {
  if (viewerInstance) {
    viewerInstance.destroy();
  }
});
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor-viewer.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
