// client/components/toastui/mermaidRenderer.js
import { createApp } from "vue";
import InteractiveMermaid from "./InteractiveMermaid.vue";

// This function is now effectively a no-op at this level. The component handles its own theme.
// It's kept for now to avoid breaking calls from the editor/viewer, but can be removed later.
export function reinitializeMermaidTheme(theme) {
  // Intentionally empty.
}

/**
 * Finds all explicitly marked Mermaid code blocks and renders them with interactive controls.
 * @param {HTMLElement} containerElement The parent element to search within.
 */
export async function renderMermaidBlocks(containerElement) {
  if (!containerElement) {
    return;
  }

  // --- CLEANUP STEP ---
  // Remove previously rendered diagrams to prevent duplication on re-render.
  const oldDiagrams = containerElement.querySelectorAll(
    ".mermaid-diagram-container",
  );
  oldDiagrams.forEach((diagramNode) => diagramNode.remove());

  // Reset the 'processed' flag on the original code blocks to allow re-rendering.
  const processedBlocks = containerElement.querySelectorAll(
    "pre[data-mermaid-processed]",
  );
  processedBlocks.forEach((block) => {
    block.removeAttribute("data-mermaid-processed");
    block.style.display = "";
  });

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

    // Create a div to mount the Vue component into
    const mountPoint = document.createElement("div");
    node.parentNode.insertBefore(mountPoint, node);
    node.style.display = "none"; // Hide the raw code block

    // Mount the Vue component
    const app = createApp(InteractiveMermaid, {
      diagramText: diagramText,
    });
    app.mount(mountPoint);

    node.setAttribute("data-mermaid-processed", "true");
  }
}
