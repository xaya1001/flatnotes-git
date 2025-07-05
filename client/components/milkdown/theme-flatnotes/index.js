// client/components/milkdown/theme-flatnotes/index.js
import { editorViewOptionsCtx } from "@milkdown/core";

import "./style.scss";

export const flatnotesTheme = (ctx) => {
  // Use the Milkdown context to update the editor view options.
  ctx.update(editorViewOptionsCtx, (prev) => {
    const prevClass = prev.attributes;

    const attributes =
      typeof prevClass === "function"
        ? (state) => {
            const attrs = prevClass(state);
            return {
              ...attrs,
              class: `${attrs?.class || ""} flatnotes-theme`,
            };
          }
        : {
            ...prevClass,
            class: `${prevClass?.class || ""} flatnotes-theme`,
          };

    return { ...prev, attributes };
  });
};
