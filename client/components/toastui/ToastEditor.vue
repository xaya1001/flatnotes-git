<template>
  <div ref="editorElement"></div>
</template>

<script setup>
import Editor from "@toast-ui/editor";
import { onMounted, onUnmounted, ref } from "vue";

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

// Overall Comment: Theme change handler is now more performant.
const handleThemeChange = () => {
  const newTheme = document.body.classList.contains("dark")
    ? "dark"
    : "default";
  reinitializeMermaidTheme(newTheme);
  runMermaidRender();
};

onMounted(() => {
  // Set initial theme before creating the editor
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
        // Overall Comment: This hook is the correct way to render.
        runMermaidRender();
        return html;
      },
    },
    hooks: props.addImageBlobHook
      ? { addImageBlobHook: props.addImageBlobHook }
      : {},
  });

  // Overall Comment: Replaced setTimeout with a more reliable direct call.
  // The 'afterPreviewRender' hook handles subsequent renders.
  // This initial call might still be needed if a preview is shown by default.
  // A slight delay might still be necessary to ensure the initial preview DOM is ready.
  // Using nextTick is better than setTimeout.
  import("vue").then(({ nextTick }) => {
    nextTick(runMermaidRender);
  });

  eventBus.on("theme-changed", handleThemeChange);
});

// Overall Comment: Unsubscribe from eventBus to prevent memory leaks.
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
