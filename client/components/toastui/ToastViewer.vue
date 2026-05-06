<template>
  <div ref="viewerElement"></div>
</template>

<script setup>
import Viewer from "@toast-ui/editor/dist/toastui-editor-viewer";
import { nextTick, onMounted, ref } from "vue";

import baseOptions from "./baseOptions.js";
import extendedAutolinks from "./extendedAutolinks.js";
import { renderMermaidBlocks } from "./mermaidRenderer.js";

const props = defineProps({
  initialValue: String,
});

const emit = defineEmits(["rendered"]);

const viewerElement = ref();

onMounted(async () => {
  new Viewer({
    ...baseOptions,
    extendedAutolinks,
    el: viewerElement.value,
    initialValue: props.initialValue,
  });

  renderMermaidBlocks(viewerElement.value);
  await nextTick();
  emit("rendered", viewerElement.value);
});
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor-viewer.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
