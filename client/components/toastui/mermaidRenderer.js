// client/components/toastui/mermaidRenderer.js
import mermaid from "mermaid";

// Comment 1: Replaced uuid with a lightweight generator
let mermaidIdCounter = 0;
function generateMermaidId() {
  return `mermaid-svg-${Date.now()}-${mermaidIdCounter++}`;
}

// Comment 2 & Security Issue: Changed securityLevel to 'strict'
// The theme is now set dynamically.
mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
});

/**
 * Dynamically re-initializes mermaid with a new theme.
 * @param {string} theme 'dark' or 'default'
 */
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

    const mermaidId = generateMermaidId();
    const mermaidInternalId = `d${mermaidId}`;

    try {
      const { svg } = await mermaid.render(mermaidInternalId, diagramText);
      const svgContainer = document.createElement("div");

      svgContainer.setAttribute("data-mermaid-svg-id", mermaidId);
      // Security Issue 1 & 2: Addressed by setting securityLevel to 'strict' in mermaid.initialize.
      // The output from mermaid is now considered safe.
      svgContainer.innerHTML = svg;

      node.parentNode.insertBefore(svgContainer, node);

      node.setAttribute("data-mermaid-processed", "true");
      node.style.display = "none";
    } catch (error) {
      console.error("Failed to render Mermaid diagram:", error);

      // Comment 3 & Security Issue 3 & 4: Use textContent to prevent XSS from error messages.
      const errorMessageNode = document.createElement("code");
      errorMessageNode.textContent = `Error rendering Mermaid diagram: ${error.message}`;
      node.innerHTML = ""; // Clear the node first
      node.appendChild(errorMessageNode);

      node.setAttribute("data-mermaid-processed", "true");

      // Clean up the temporary error SVG that mermaid might create in the DOM body
      const mermaidErrorSvg = document.getElementById(mermaidInternalId);
      if (mermaidErrorSvg) {
        mermaidErrorSvg.remove();
      }
    }
  }
}
