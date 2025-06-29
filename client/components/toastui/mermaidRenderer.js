// client/components/toastui/mermaidRenderer.js
import mermaid from "mermaid";
import { v4 as uuidv4 } from "uuid"; // Import the uuid library

// Initialize Mermaid only once with our desired settings.
mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
});

/**
 * Finds all explicitly marked Mermaid code blocks (` ```mermaid `) within a given
 * container and renders them into SVG diagrams.
 * @param {HTMLElement} containerElement The parent element to search within.
 */
export async function renderMermaidBlocks(containerElement) {
  if (!containerElement) {
    return;
  }

  // --- CLEANUP STEP ---
  // Remove previously rendered SVGs and reset the state of processed <pre> blocks.
  const oldSvgs = containerElement.querySelectorAll("div[data-mermaid-svg-id]");
  oldSvgs.forEach((svgNode) => svgNode.remove());

  const processedBlocks = containerElement.querySelectorAll(
    "pre[data-mermaid-processed]",
  );
  processedBlocks.forEach((block) => {
    block.removeAttribute("data-mermaid-processed");
    block.style.display = ""; // Restore visibility before re-processing
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

    // Use UUID for a more robust and unique ID.
    const mermaidId = `mermaid-svg-${uuidv4()}`;
    // Mermaid's internal render function requires the ID to start with a letter.
    const mermaidInternalId = `d${mermaidId}`;

    try {
      const { svg } = await mermaid.render(mermaidInternalId, diagramText);
      const svgContainer = document.createElement("div");

      // Use a data-attribute for the SVG container's ID for clarity and easier selection.
      svgContainer.setAttribute("data-mermaid-svg-id", mermaidId);
      svgContainer.innerHTML = svg;

      node.parentNode.insertBefore(svgContainer, node);

      node.setAttribute("data-mermaid-processed", "true");
      node.style.display = "none";
    } catch (error) {
      console.error("Failed to render Mermaid diagram:", error);
      // Display error inside the code block itself for user feedback.
      node.innerHTML = `<code>Error rendering Mermaid diagram: ${error.message}</code>`;
      node.setAttribute("data-mermaid-processed", "true");
    }
  }
}
