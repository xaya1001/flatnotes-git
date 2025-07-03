<!-- client/components/toastui/InteractiveMermaid.vue -->
<template>
  <div
    data-mermaid-wrapper
    class="mermaid-diagram-container"
    :class="{
      'has-error': !!errorMessage,
      'is-panning': isSpacePressed,
    }"
    ref="container"
    @mousedown="handleMouseDown"
  >
    <!-- Wrapper for overflow and custom panning/zooming -->
    <div class="mermaid-scroll-wrapper">
      <!-- The target where the SVG or error message will be rendered -->
      <div class="mermaid-render-target" :style="transformStyle">
        <!-- Render error box if rendering fails -->
        <div v-if="errorMessage" class="mermaid-error-box">
          <h4 class="mermaid-error-title">Mermaid Render Error</h4>
          <pre class="mermaid-error-text">{{ errorMessage }}</pre>
        </div>
        <!-- Render SVG content if successful -->
        <div
          v-else-if="svgContent"
          class="svg-wrapper"
          v-html="svgContent"
        ></div>
      </div>
    </div>

    <!-- Controls are positioned relative to the main container -->
    <div v-if="!errorMessage" class="mermaid-controls">
      <button title="Copy Source" @click="copySource" :disabled="isCopied">
        <SvgIcon v-if="isCopied" type="mdi" :path="mdiCheck" :size="18" />
        <SvgIcon v-else type="mdi" :path="mdiContentCopy" :size="18" />
      </button>
      <button title="Zoom In" @click="zoomIn">
        <SvgIcon type="mdi" :path="mdiMagnifyPlus" :size="18" />
      </button>
      <button title="Zoom Out" @click="zoomOut">
        <SvgIcon type="mdi" :path="mdiMagnifyMinus" :size="18" />
      </button>
      <button title="Reset View" @click="resetView">
        <SvgIcon type="mdi" :path="mdiRestore" :size="18" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import mermaid from "mermaid";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdiContentCopy,
  mdiMagnifyPlus,
  mdiMagnifyMinus,
  mdiRestore,
  mdiCheck,
} from "@mdi/js";

const props = defineProps({
  diagramText: { type: String, required: true },
});

// --- State Refs ---
const container = ref(null);
const scale = ref(1);
const panX = ref(0);
const panY = ref(0);
const isSpacePressed = ref(false); // Activates panning mode
const isPanning = ref(false); // True while mouse is down in panning mode
let panStart = { x: 0, y: 0 };

const isCopied = ref(false);
const errorMessage = ref(null);
const svgContent = ref("");
let themeObserver = null;

const ZOOM_BUTTON_FACTOR = 1.25;
const MAX_SCALE = 8;
const MIN_SCALE = 0.2;

// --- Computed Properties ---
// Computes the transform style for pan and zoom
const transformStyle = computed(() => {
  return `transform: translate(${panX.value}px, ${panY.value}px) scale(${scale.value});`;
});

// --- Core Rendering Logic ---
// Initializes Mermaid and renders the diagram text
const initializeAndRender = async (theme) => {
  if (!props.diagramText.trim()) return;

  // Reset state before rendering
  errorMessage.value = null;
  svgContent.value = "";
  resetView();

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: theme,
    // Ensure text is selectable in the final SVG
    flowchart: { useMaxWidth: false },
    sequence: { useMaxWidth: false },
  });

  const mermaidId = `mermaid-id-${Math.random().toString(36).substring(2, 9)}`;

  try {
    // Renders to an off-screen div to prevent Mermaid's default error UI.
    // This is the key to preventing the "bomb" icon on syntax errors.
    const { svg } = await mermaid.render(mermaidId, props.diagramText);
    svgContent.value = svg;
  } catch (error) {
    console.error("Failed to render Mermaid diagram:", error);
    errorMessage.value = error.message;
  }
};

// --- Event Handlers for Pan and Zoom ---
const handleMouseDown = (e) => {
  // Only start panning if spacebar is held down
  if (isSpacePressed.value) {
    e.preventDefault(); // Prevents text selection during pan
    isPanning.value = true;
    panStart.x = e.clientX - panX.value;
    panStart.y = e.clientY - panY.value;
  }
};

const handleMouseMove = (e) => {
  if (!isPanning.value) return;
  panX.value = e.clientX - panStart.x;
  panY.value = e.clientY - panStart.y;
};

const handleMouseUp = () => {
  isPanning.value = false;
};

const handleWheel = (e) => {
  // Only zoom if Ctrl or Cmd key is held down
  if (!e.ctrlKey && !e.metaKey) return;
  e.preventDefault();

  const scaleFactor = e.deltaY > 0 ? 1 / 1.1 : 1.1;
  const newScale = Math.max(
    MIN_SCALE,
    Math.min(scale.value * scaleFactor, MAX_SCALE),
  );

  // Get mouse position relative to the container
  const rect = container.value.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;

  // Adjust pan to zoom towards the mouse pointer
  panX.value = mouseX - (mouseX - panX.value) * (newScale / scale.value);
  panY.value = mouseY - (mouseY - panY.value) * (newScale / scale.value);
  scale.value = newScale;
};

// --- UI Control Actions ---
const zoomIn = () => {
  scale.value = Math.min(scale.value * ZOOM_BUTTON_FACTOR, MAX_SCALE);
};
const zoomOut = () => {
  scale.value = Math.max(scale.value / ZOOM_BUTTON_FACTOR, MIN_SCALE);
};
const resetView = () => {
  scale.value = 1;
  panX.value = 0;
  panY.value = 0;
};
const copySource = async () => {
  if (isCopied.value) return;
  try {
    await navigator.clipboard.writeText(props.diagramText);
    isCopied.value = true;
    setTimeout(() => {
      isCopied.value = false;
    }, 1500); // Reset after 1.5 seconds
  } catch (err) {
    console.error("Failed to copy diagram source:", err);
  }
};

// --- Lifecycle Hooks ---
onMounted(() => {
  const initialTheme = document.body.classList.contains("dark")
    ? "dark"
    : "default";
  initializeAndRender(initialTheme);

  // Add global event listeners
  window.addEventListener("mousemove", handleMouseMove);
  window.addEventListener("mouseup", handleMouseUp);
  container.value.addEventListener("wheel", handleWheel, { passive: false });

  // Spacebar listener for panning mode
  const handleKeydown = (e) => {
    if (e.code === "Space") isSpacePressed.value = true;
  };
  const handleKeyup = (e) => {
    if (e.code === "Space") isSpacePressed.value = false;
  };
  window.addEventListener("keydown", handleKeydown);
  window.addEventListener("keyup", handleKeyup);

  // Theme change observer
  themeObserver = new MutationObserver(() => {
    const newTheme = document.body.classList.contains("dark")
      ? "dark"
      : "default";
    initializeAndRender(newTheme);
  });
  themeObserver.observe(document.body, {
    attributes: true,
    attributeFilter: ["class"],
  });

  // Cleanup listeners on unmount
  onUnmounted(() => {
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
    if (container.value) {
      container.value.removeEventListener("wheel", handleWheel);
    }
    window.removeEventListener("keydown", handleKeydown);
    window.removeEventListener("keyup", handleKeyup);
    if (themeObserver) themeObserver.disconnect();
  });
});

// Re-render when the source text changes
watch(
  () => props.diagramText,
  () => {
    const currentTheme = document.body.classList.contains("dark")
      ? "dark"
      : "default";
    initializeAndRender(currentTheme);
  },
);
</script>
