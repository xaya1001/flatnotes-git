// client/components/toastui/mermaidRenderer.js
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

  // Find all previously created component wrappers.
  const oldWrappers = containerElement.querySelectorAll(`.${WRAPPER_CLASS}`);
  oldWrappers.forEach((wrapperNode) => {
    // Unmount the Vue app instance associated with this wrapper.
    if (componentInstanceMap.has(wrapperNode)) {
      componentInstanceMap.get(wrapperNode).unmount();
      componentInstanceMap.delete(wrapperNode);
    }
    // Remove the wrapper div from the DOM.
    wrapperNode.remove();
  });

  // Reset the 'processed' flag on the original code blocks to allow re-rendering.
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

  // --- CLEANUP STEP ---
  // Always clean up previous renders before creating new ones.
  cleanupMermaidRenders(containerElement);

  // --- SELECTION STEP ---
  const mermaidNodes = containerElement.querySelectorAll("pre.lang-mermaid");
  if (mermaidNodes.length === 0) {
    return;
  }

  // --- RENDER STEP ---
  for (const node of mermaidNodes) {
    if (node.getAttribute("data-mermaid-processed")) {
      continue;
    }

    const diagramText = node.textContent;
    if (!diagramText.trim()) {
      continue;
    }

    // Create a dedicated wrapper div to mount the Vue component into.
    const mountPoint = document.createElement("div");
    mountPoint.className = WRAPPER_CLASS;
    node.parentNode.insertBefore(mountPoint, node);
    node.style.display = "none"; // Hide the raw code block

    // Create and mount the Vue component.
    const app = createApp(InteractiveMermaid, {
      diagramText: diagramText,
    });
    app.mount(mountPoint);

    // Store the app instance with its mount point as the key.
    componentInstanceMap.set(mountPoint, app);

    node.setAttribute("data-mermaid-processed", "true");
  }
}
