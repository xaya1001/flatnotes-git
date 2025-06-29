<template>
  <div ref="editorElement"></div>
</template>

<script setup>
import Editor from "@toast-ui/editor";
import { onMounted, ref } from "vue";

import eventBus from "../../git-integration/services/eventBus.js";
import baseOptions from "./baseOptions.js";
import { renderMermaidBlocks } from "./mermaidRenderer.js";

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

const runMermaidRender = (renderer) => {
  if (editorElement.value) {
    (renderer || renderMermaidBlocks)(editorElement.value);
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

  setTimeout(runMermaidRender, 100);

  eventBus.on("theme-changed", async () => {
    const { renderMermaidBlocks } = await import(
      "./mermaidRenderer.js?t=" + new Date().getTime()
    );
    runMermaidRender(renderMermaidBlocks);
  });
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
