<template>
  <Milkdown />
</template>

<script setup>
import {
  Editor,
  defaultValueCtx,
  editorViewOptionsCtx,
  rootCtx,
} from "@milkdown/core";
import { listener, listenerCtx } from "@milkdown/kit/plugin/listener";
import { replaceAll } from "@milkdown/utils";
import { Milkdown, useEditor, useInstance } from "@milkdown/vue";
import { ref, watch } from "vue";

import { configureBase, basePlugins } from "./milkdown-base";

const props = defineProps({
  initialValue: { type: String, default: "" },
  readOnly: { type: Boolean, default: false },
  addImageBlobHook: { type: Function, default: () => {} },
});
const emit = defineEmits(["change", "keydown"]);
const currentMarkdownValue = ref(props.initialValue);

const [loading, getEditor] = useInstance();

useEditor((root) => {
  return Editor.make()
    .config((ctx) => {
      ctx.set(rootCtx, root);
      ctx.set(defaultValueCtx, props.initialValue);

      // Editor-specific config
      ctx.update(editorViewOptionsCtx, (prev) => ({
        ...prev,
        editable: () => !props.readOnly,
        handleKeyDown: (_, event) => {
          emit("keydown", event);
          return false;
        },
      }));

      // Editor-specific listener
      ctx.get(listenerCtx).markdownUpdated((_, markdown) => {
        currentMarkdownValue.value = markdown;
        if (!props.readOnly) {
          emit("change");
        }
      });

      configureBase(ctx);
    })
    .use(basePlugins)
    .use(listener);
});

watch(
  () => props.initialValue,
  (newValue) => {
    if (loading.value) return;
    const editor = getEditor();
    if (editor) {
      editor.action(replaceAll(newValue || ""));
    }
  },
);
const getMarkdown = () => currentMarkdownValue.value;
defineExpose({ getMarkdown });
</script>
