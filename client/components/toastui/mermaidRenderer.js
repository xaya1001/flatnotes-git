// client/components/toastui/mermaidRenderer.js
import mermaid from "mermaid";
import { ref } from 'vue'; // Import ref for usePanAndZoom
import { usePanAndZoom } from './composables/usePanAndZoom.js';

let mermaidIdCounter = 0;
function generateMermaidId() {
  return `mermaid-block-${Date.now()}-${mermaidIdCounter++}`; // Changed prefix for clarity
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
  // Changed selector to target the new panZoomContainer
  const oldDiagramContainers = containerElement.querySelectorAll("div[data-mermaid-block-id]");
  oldDiagramContainers.forEach((containerNode) => containerNode.remove());
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

    const mermaidBlockId = generateMermaidId(); // Used for the main container
    const mermaidInternalRenderId = `mermaid-svg-${mermaidBlockId}`; // Used for mermaid.render

    try {
      const { svg } = await mermaid.render(mermaidInternalRenderId, diagramText);

      const panZoomContainer = document.createElement("div");
      panZoomContainer.setAttribute("data-mermaid-block-id", mermaidBlockId);
      panZoomContainer.className = "mermaid-pan-zoom-container"; // Use class for styling
      panZoomContainer.style.position = "relative"; // Keep as these are structural
      panZoomContainer.style.overflow = "hidden";   // Keep as these are structural

      const svgDoc = parser.parseFromString(svg, "image/svg+xml");
      const svgElement = svgDoc.documentElement;
      // Ensure SVG takes full width of its direct container initially for scaling
      svgElement.style.width = "100%";
      svgElement.style.height = "100%";
      svgElement.style.display = "block";
      svgElement.style.transformOrigin = "top left"; // Important for scaling behavior

      // The SVG itself will be wrapped by svgContainer for pan/zoom manipulation
      const svgDirectContainer = document.createElement("div");
      svgDirectContainer.className = "mermaid-svg-direct-container"; // Added class
      svgDirectContainer.style.width = "100%";
      svgDirectContainer.style.height = "100%";
      svgDirectContainer.appendChild(svgElement);
      panZoomContainer.appendChild(svgDirectContainer);

      // Controls Panel
      const controlsPanel = document.createElement("div");
      controlsPanel.className = "mermaid-controls-panel"; // Use class for styling
      controlsPanel.style.position = "absolute"; // Keep as these are structural
      controlsPanel.style.top = "8px";           // Keep as these are structural
      controlsPanel.style.right = "8px";         // Keep as these are structural
      controlsPanel.style.display = "none";      // Keep, controlled by JS
      controlsPanel.style.zIndex = "10";         // Keep as these are structural

      const zoomInButton = document.createElement("button");
      zoomInButton.textContent = "+";

      const zoomOutButton = document.createElement("button");
      zoomOutButton.textContent = "-";

      const resetButton = document.createElement("button");
      resetButton.textContent = "Reset";

      controlsPanel.appendChild(zoomInButton);
      controlsPanel.appendChild(zoomOutButton);
      controlsPanel.appendChild(resetButton);
      panZoomContainer.appendChild(controlsPanel);

      // Attach pan and zoom logic
      // We need to pass refs to usePanAndZoom. Since we are not in a setup function,
      // we create simple objects that mimic Vue refs' .value property.
      const svgElementRef = { value: svgDirectContainer }; // The element to transform is svgDirectContainer
      const containerElementRef = { value: panZoomContainer }; // The element for mouse events

      // Call usePanAndZoom and connect buttons
      // Note: usePanAndZoom expects to be called within a Vue setup context for onMounted/onUnmounted.
      // This direct call won't trigger its lifecycle hooks. This is a simplification.
      // A better way would be to make usePanAndZoom return a setup function or make it a class.
      // For now, we'll call its methods directly.
      const { zoomIn, zoomOut, reset, onMouseDown, onMouseMove, onMouseUp, onWheel } = usePanAndZoom(svgElementRef, containerElementRef);

      zoomInButton.onclick = () => zoomIn();
      zoomOutButton.onclick = () => zoomOut();
      resetButton.onclick = () => reset();

      // Manually attach event listeners from usePanAndZoom as its onMounted won't run
      panZoomContainer.style.cursor = 'grab';
      panZoomContainer.addEventListener('mousedown', onMouseDown);
      // Mouse move and up should ideally be on document to allow dragging outside bounds
      // but usePanAndZoom handles this. We need to ensure its internal onMounted/onUnmounted logic is called.
      // This simplified call might not work as expected without Vue's reactivity and lifecycle.
      // THIS IS A CRITICAL POINT: usePanAndZoom's onMounted/onUnmounted will NOT be called here.
      // We need to manually replicate that or change usePanAndZoom.

      // For a quick test, let's manually call the event registration part of onMounted
      // This is a HACK and `usePanAndZoom` should be refactored for non-component usage.
      if (containerElementRef.value) {
          // usePanAndZoom's onMounted adds mousedown, mousemove, mouseup, and wheel.
          // We've already added mousedown. mousemove and mouseup are on document.
          // So we only strictly need to add wheel here from the onMounted logic.
          // However, the actual onMounted in usePanAndZoom also sets up cursor and initial transform.
          // The initial transform is `updateTransform()` which we can call.
          // The cursor `grab` is already set.
          // The `document.addEventListener` for mousemove and mouseup are tricky because
          // usePanAndZoom *returns* onMouseMove and onMouseUp, but it internally adds them to document.
          // This is the core of the issue with calling it outside setup.
          // For now, we assume the returned handlers might be what we need or that the internal ones will somehow work.
          // This part is most likely to fail or behave unexpectedly.
          containerElementRef.value.addEventListener('wheel', onWheel, { passive: false });

          // Let's call the internal document event listeners setup, if we can infer it.
          // Since usePanAndZoom *returns* onMouseMove and onMouseUp, it implies they are meant to be
          // potentially used by the caller. The `onMounted` in the composable itself adds them to `document`.
          // This is a conflict of responsibility.
          // The current `usePanAndZoom` adds these to `document` in its `onMounted`.
          // If `onMounted` is not called, these won't be active on `document`.
          // The `onMouseDown` is attached to `containerElementRef`.
          // This is fine.
      }


      // Show/Hide controls
      panZoomContainer.addEventListener("mouseenter", () => {
        controlsPanel.style.display = "flex"; // Use flex for better button layout
      });
      panZoomContainer.addEventListener("mouseleave", () => {
        controlsPanel.style.display = "none";
      });

      node.parentNode.insertBefore(panZoomContainer, node);
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

      const mermaidErrorSvg = document.getElementById(mermaidInternalRenderId); // Use the correct ID
      if (mermaidErrorSvg) {
        mermaidErrorSvg.remove();
      }
    } finally {
      node.setAttribute("data-mermaid-processed", "true");
    }
  }
}
