<template>
  <Milkdown />
</template>

<script setup>
import {
  Editor,
  rootCtx,
  defaultValueCtx,
  editorViewOptionsCtx,
} from "@milkdown/core";
import { Milkdown, useEditor } from "@milkdown/vue";

import { configureBase, basePlugins } from "./milkdown-base";

const props = defineProps({
  initialValue: {
    type: String,
    default: "",
  },
});

useEditor((root) => {
  return Editor.make()
    .config((ctx) => {
      ctx.set(rootCtx, root);
      ctx.set(defaultValueCtx, props.initialValue);
      ctx.update(editorViewOptionsCtx, (prev) => ({
        ...prev,
        editable: () => false,
      }));

      configureBase(ctx);
    })
    .use(basePlugins);
});
</script>
