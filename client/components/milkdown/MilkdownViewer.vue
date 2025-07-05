<!-- client/components/milkdown/MilkdownViewer.vue -->
<template>
  <Milkdown />
</template>

<script setup>
import { Milkdown, useEditor } from "@milkdown/vue";
import {
  Editor,
  rootCtx,
  defaultValueCtx,
  editorViewOptionsCtx,
} from "@milkdown/kit/core";
import { commonmark } from "@milkdown/kit/preset/commonmark";
import { gfm } from "@milkdown/kit/preset/gfm";
import { prism } from "@milkdown/plugin-prism";

import {
  listItemBlockComponent,
  listItemBlockConfig,
} from "@milkdown/kit/component/list-item-block";

import { flatnotesTheme } from "./theme-flatnotes";
import { checkedCheckbox, uncheckedCheckbox } from "./theme-flatnotes/icons";

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

      ctx.set(listItemBlockConfig.key, {
        renderLabel: ({ listType, label, checked }) => {
          if (checked != null) {
            return checked ? checkedCheckbox : uncheckedCheckbox;
          }

          if (listType === "bullet") {
            return "<span>•</span>";
          }

          return label;
        },
      });
    })
    .use(commonmark)
    .use(gfm)
    .use(prism)
    .use(flatnotesTheme)
    .use(listItemBlockComponent);
});
</script>
