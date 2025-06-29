<template>
  <div ref="editorElement"></div>
</template>

<script setup>
import Editor from "@toast-ui/editor";
import { onMounted, onUnmounted, ref, nextTick } from "vue";

import eventBus from "../../git-integration/services/eventBus.js";
import baseOptions from "./baseOptions.js";
import {
  renderMermaidBlocks,
  reinitializeMermaidTheme,
} from "./mermaidRenderer.js";

const props = defineProps({
  initialValue: String,
  initialEditType: {
    type: String,
    default: "markdown",
  },
  addImageBlobHook: Function,
});

const emit = defineEmits(["change", "keydown"]);

const editorElement = ref();
let toastEditor;

const runMermaidRender = () => {
  if (editorElement.value) {
    renderMermaidBlocks(editorElement.value);
  }
};

const handleThemeChange = () => {
  const newTheme = document.body.classList.contains("dark")
    ? "dark"
    : "default";
  reinitializeMermaidTheme(newTheme);
  runMermaidRender();
};

onMounted(() => {
  const initialTheme = document.body.classList.contains("dark")
    ? "dark"
    : "default";
  reinitializeMermaidTheme(initialTheme);

  toastEditor = new Editor({
    ...baseOptions,
    el: editorElement.value,
    initialValue: props.initialValue,
    initialEditType: props.initialEditType,
    events: {
      change: () => {
        emit("change");
      },
      keydown: (_, event) => {
        emit("keydown", event);
      },
      afterPreviewRender: (html) => {
        runMermaidRender();
        return html;
      },
    },
    hooks: props.addImageBlobHook
      ? { addImageBlobHook: props.addImageBlobHook }
      : {},
  });

  nextTick(runMermaidRender);

  eventBus.on("theme-changed", handleThemeChange);
});

onUnmounted(() => {
  eventBus.off("theme-changed", handleThemeChange);
});

function getMarkdown() {
  return toastEditor.getMarkdown();
}

function isWysiwygMode() {
  return toastEditor.isWysiwygMode();
}

defineExpose({ getMarkdown, isWysiwygMode });
</script>

<style>
@import "@toast-ui/editor/dist/toastui-editor.css";
@import "prismjs/themes/prism.css";
@import "@toast-ui/editor-plugin-code-syntax-highlight/dist/toastui-editor-plugin-code-syntax-highlight.css";
@import "./toastui-editor-overrides.scss";
</style>
