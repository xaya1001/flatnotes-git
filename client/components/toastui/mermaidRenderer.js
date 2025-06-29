// client/components/toastui/mermaidRenderer.js
import mermaid from "mermaid";

let mermaidIdCounter = 0;
function generateMermaidId() {
  return `mermaid-svg-${Date.now()}-${mermaidIdCounter++}`;
}

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
});

export function reinitializeMermaidTheme(theme) {
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: theme,
  });
}

/**
 * Finds all explicitly marked Mermaid code blocks and renders them.
 * @param {HTMLElement} containerElement The parent element to search within.
 */
export async function renderMermaidBlocks(containerElement) {
  if (!containerElement) {
    return;
  }

  // --- CLEANUP STEP ---
  const oldSvgs = containerElement.querySelectorAll("div[data-mermaid-svg-id]");
  oldSvgs.forEach((svgNode) => svgNode.remove());
  const oldErrors = containerElement.querySelectorAll(
    "div[data-mermaid-error]",
  );
  oldErrors.forEach((errorNode) => errorNode.remove());

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

  const parser = new DOMParser();

  // --- RENDER STEP ---
  for (const node of mermaidNodes) {
    if (node.getAttribute("data-mermaid-processed")) {
      continue;
    }

    const diagramText = node.textContent;
    if (!diagramText.trim()) {
      continue;
    }

    const mermaidId = generateMermaidId();
    const mermaidInternalId = `d${mermaidId}`;

    try {
      const { svg } = await mermaid.render(mermaidInternalId, diagramText);
      const svgContainer = document.createElement("div");
      svgContainer.setAttribute("data-mermaid-svg-id", mermaidId);

      const svgDoc = parser.parseFromString(svg, "image/svg+xml");
      const svgElement = svgDoc.documentElement;
      svgContainer.appendChild(svgElement);

      node.parentNode.insertBefore(svgContainer, node);
      node.style.display = "none";
    } catch (error) {
      console.error("Failed to render Mermaid diagram:", error);

      const errorContainer = document.createElement("div");
      errorContainer.setAttribute("data-mermaid-error", "true");
      errorContainer.style.color = "red";
      errorContainer.style.padding = "10px";
      errorContainer.style.border = "1px solid red";
      errorContainer.style.borderRadius = "4px";
      errorContainer.textContent = `Error rendering Mermaid diagram: ${error.message}`;
      node.parentNode.insertBefore(errorContainer, node);
      node.style.display = "none";

      const mermaidErrorSvg = document.getElementById(mermaidInternalId);
      if (mermaidErrorSvg) {
        mermaidErrorSvg.remove();
      }
    } finally {
      node.setAttribute("data-mermaid-processed", "true");
    }
  }
}
