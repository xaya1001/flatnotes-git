import { commonmark } from "@milkdown/preset-commonmark";
import { gfm } from "@milkdown/preset-gfm";
import {
  listItemBlockComponent,
  listItemBlockConfig,
} from "@milkdown/kit/component/list-item-block";
import { prism } from "@milkdown/plugin-prism";

import { flatnotesTheme } from "./theme-flatnotes";
import { checkedCheckbox, uncheckedCheckbox } from "./theme-flatnotes/icons";

export const configureBase = (ctx) => {
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
};

export const basePlugins = [
  commonmark,
  gfm,
  flatnotesTheme,
  listItemBlockComponent,
  prism,
];
