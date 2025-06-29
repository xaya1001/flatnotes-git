// client/components/toastui/mermaidRenderer.js
import mermaid from "mermaid";
import { v4 as uuidv4 } from "uuid";

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
  const oldSvgs = containerElement.querySelectorAll("div[data-mermaid-svg-id]");
  oldSvgs.forEach((svgNode) => svgNode.remove());

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

    const mermaidId = `mermaid-svg-${uuidv4()}`;
    const mermaidInternalId = `d${mermaidId}`;

    try {
      const { svg } = await mermaid.render(mermaidInternalId, diagramText);
      const svgContainer = document.createElement("div");

      svgContainer.setAttribute("data-mermaid-svg-id", mermaidId);
      svgContainer.innerHTML = svg;

      node.parentNode.insertBefore(svgContainer, node);

      node.setAttribute("data-mermaid-processed", "true");
      node.style.display = "none";
    } catch (error) {
      console.error("Failed to render Mermaid diagram:", error);
      node.innerHTML = `<code>Error rendering Mermaid diagram: ${error.message}</code>`;
      node.setAttribute("data-mermaid-processed", "true");
    }
  }
}
