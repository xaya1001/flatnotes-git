<template>
  <div ref="editorElement"></div>
</template>

<script setup>
import Editor from "@toast-ui/editor";
import { onMounted, onUnmounted, ref, nextTick } from "vue";
import baseOptions from "./baseOptions.js";
import {
  renderMermaidBlocks,
  cleanupMermaidRenders,
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

onMounted(() => {
  toastEditor = new Editor({
    ...baseOptions,
    el: editorElement.value,
    initialValue: props.initialValue,
    initialEditType: props.initialEditType,
    events: {
      change: () => {
        emit("change");
        // Re-render is needed on 'change' to support live updates in WYSIWYG mode.
        // For Markdown mode, the preview pane is handled by `afterPreviewRender`.
        nextTick(runMermaidRender);
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
});

onUnmounted(() => {
  // CRITICAL FIX: Clean up any mounted Mermaid components when editor is destroyed.
  if (editorElement.value) {
    cleanupMermaidRenders(editorElement.value);
  }
  if (toastEditor) {
    toastEditor.destroy();
  }
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
