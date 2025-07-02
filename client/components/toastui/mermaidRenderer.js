// client/components/toastui/mermaidRenderer.js
import { onMounted, onUnmounted, nextTick } from "vue";
import { createApp } from "vue";
import InteractiveMermaid from "./InteractiveMermaid.vue";

const componentInstanceMap = new WeakMap();
const WRAPPER_CLASS = "mermaid-component-wrapper";

/**
 * Cleans up any previously rendered Mermaid Vue components within a given container.
 * This is crucial for preventing state leakage when navigating between notes.
 * @param {HTMLElement} containerElement The parent element to clean up.
 */
export function cleanupMermaidRenders(containerElement) {
  if (!containerElement) return;

  const oldWrappers = containerElement.querySelectorAll(`.${WRAPPER_CLASS}`);
  oldWrappers.forEach((wrapperNode) => {
    if (componentInstanceMap.has(wrapperNode)) {
      componentInstanceMap.get(wrapperNode).unmount();
      componentInstanceMap.delete(wrapperNode);
    }
    wrapperNode.remove();
  });

  const processedBlocks = containerElement.querySelectorAll(
    "pre[data-mermaid-processed]",
  );
  processedBlocks.forEach((block) => {
    block.removeAttribute("data-mermaid-processed");
    block.style.display = "";
  });
}

/**
 * Finds all explicitly marked Mermaid code blocks and renders them with interactive controls.
 * @param {HTMLElement} containerElement The parent element to search within.
 */
export async function renderMermaidBlocks(containerElement) {
  if (!containerElement) return;

  cleanupMermaidRenders(containerElement);

  const mermaidNodes = containerElement.querySelectorAll("pre.lang-mermaid");
  if (mermaidNodes.length === 0) {
    return;
  }

  for (const node of mermaidNodes) {
    if (node.getAttribute("data-mermaid-processed")) {
      continue;
    }

    const diagramText = node.textContent;
    if (!diagramText.trim()) {
      continue;
    }

    const mountPoint = document.createElement("div");
    mountPoint.className = WRAPPER_CLASS;
    node.parentNode.insertBefore(mountPoint, node);
    node.style.display = "none";

    const app = createApp(InteractiveMermaid, {
      diagramText: diagramText,
    });
    app.mount(mountPoint);

    componentInstanceMap.set(mountPoint, app);

    node.setAttribute("data-mermaid-processed", "true");
  }
}

/**
 * A composable to manage the lifecycle of Mermaid diagrams within a ToastUI component.
 * @param {import('vue').Ref<HTMLElement>} elementRef - The ref pointing to the container element.
 */
export function useMermaidRenderer(elementRef) {
  const render = () => {
    nextTick(() => {
      if (elementRef.value) {
        renderMermaidBlocks(elementRef.value);
      }
    });
  };

  const cleanup = () => {
    if (elementRef.value) {
      cleanupMermaidRenders(elementRef.value);
    }
  };

  onMounted(render);
  onUnmounted(cleanup);

  return { render, cleanup };
}