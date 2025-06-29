// /client/components/toastui/mermaidRenderer.js
import mermaid from "mermaid";

// Initialize Mermaid only once with our desired settings.
mermaid.initialize({
  startOnLoad: false,
  theme: "default",
  securityLevel: "loose",
});

/**
 * Finds all 'custom-mermaid-block' elements within a given container
 * and renders them using a manual, non-destructive approach.
 * @param {HTMLElement} containerElement The parent element to search within.
 */
export async function renderMermaidBlocks(containerElement) {
  if (!containerElement) {
    return;
  }

  // --- CLEANUP STEP ---
  // Before rendering, remove all previously generated Mermaid SVGs within this container.
  // We identify them by the 'id' we ask Mermaid to generate.
  const oldSvgs = containerElement.querySelectorAll('div[id^="mermaid-svg-"]');
  oldSvgs.forEach((svgNode) => svgNode.remove());
  // And also remove the 'data-processed' attribute from all blocks to make them "renderable" again.
  const processedBlocks = containerElement.querySelectorAll(
    "pre.custom-mermaid-block[data-processed]",
  );
  processedBlocks.forEach((block) => block.removeAttribute("data-processed"));

  // Find all elements that we "tagged" in baseOptions.js.
  // Now we just look for the class, regardless of the data-processed attribute.
  const mermaidNodes = containerElement.querySelectorAll(
    "pre.custom-mermaid-block",
  );

  if (mermaidNodes.length === 0) {
    return;
  }

  // Process each found node individually.
  for (const node of mermaidNodes) {
    // If it's already processed by this run, skip.
    if (node.getAttribute("data-processed")) {
      continue;
    }

    const diagramText = node.textContent;
    // The ID now needs to be attached to the SVG container itself for cleanup.
    const mermaidId = `mermaid-svg-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

    try {
      // 1. Ask Mermaid to render the diagram into an SVG string in memory.
      const { svg } = await mermaid.render(`d${mermaidId}`, diagramText); // Mermaid requires ID to start with a letter

      // 2. Create a new container element for our SVG.
      const svgContainer = document.createElement("div");
      // Set the ID on our container for future cleanup.
      svgContainer.id = mermaidId;
      svgContainer.innerHTML = svg;

      // 3. Insert the new container with the rendered SVG right before the original <pre> block.
      node.parentNode.insertBefore(svgContainer, node);

      // 4. Mark the original <pre> block as "processed" to prevent re-rendering
      //    and to allow our CSS to hide it.
      node.setAttribute("data-processed", "true");
    } catch (error) {
      console.error("Failed to render Mermaid diagram:", error);
      node.innerHTML = `Error rendering Mermaid diagram: ${error.message}`;
      node.setAttribute("data-processed", "true");
    }
  }
}
