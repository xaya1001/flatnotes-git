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
          ref="svgWrapper"
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
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
const svgWrapper = ref(null);
const scale = ref(1);
const panX = ref(0);
const panY = ref(0);
const isSpacePressed = ref(false);
const isPanning = ref(false);
let panStart = { x: 0, y: 0 };

const isCopied = ref(false);
const errorMessage = ref(null);
const svgContent = ref("");

const ZOOM_BUTTON_FACTOR = 1.25;
const MAX_SCALE = 8;
const MIN_SCALE = 0.2;

// --- Computed Properties ---
const transformStyle = computed(() => {
  return `transform: translate(${panX.value}px, ${panY.value}px) scale(${scale.value});`;
});

/**
 * Reads a CSS variable from the document's root element.
 * @param {string} name - The name of the CSS variable (e.g., '--theme-text').
 * @returns {string} The trimmed value of the variable.
 */
const getThemeColor = (name) => {
  // Fallback to a default color if the CSS variable is not available (e.g., in tests)
  if (typeof window === "undefined") return "#000000";
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
};

// --- Core Rendering Logic ---
const initializeAndRender = async () => {
  if (!props.diagramText.trim()) return;

  errorMessage.value = null;
  svgContent.value = "";
  resetView();

  const isDarkMode =
    typeof document !== "undefined" && document.body.classList.contains("dark");

  // THE KEY FIX: `darkMode` is a top-level property, not inside `themeVariables`.
  mermaid.initialize({
    // Behavior
    startOnLoad: false,
    securityLevel: "strict",
    suppressErrorRendering: true,

    // Theming
    theme: "base",
    fontFamily: '"Poppins", sans-serif',
    darkMode: isDarkMode, // Correctly placed at the top level

    // Theme Variables for deep customization
    themeVariables: {
      background: getThemeColor("--theme-background"),
      primaryColor: getThemeColor("--theme-background-elevated"),
      primaryTextColor: getThemeColor("--theme-text"),
      primaryBorderColor: getThemeColor("--theme-border"),
      lineColor: getThemeColor("--theme-border"),
      textColor: getThemeColor("--theme-text"),
      actorBkg: getThemeColor("--theme-background-elevated"),
      actorBorder: getThemeColor("--theme-border"),
      actorTextColor: getThemeColor("--theme-text"),
      signalColor: getThemeColor("--theme-text"),
      signalTextColor: getThemeColor("--theme-text"),
    },
  });

  const mermaidId = `mermaid-id-${Math.random().toString(36).substring(2, 9)}`;

  try {
    const { svg, bindFunctions } = await mermaid.render(
      mermaidId,
      props.diagramText,
    );
    svgContent.value = svg;

    await nextTick();
    if (bindFunctions && svgWrapper.value) {
      bindFunctions(svgWrapper.value);
    }
  } catch (error) {
    console.error("Failed to render Mermaid diagram:", error);
    errorMessage.value = error.message;
  }
};

// --- Event Handlers and UI Actions (UNCHANGED) ---
const handleMouseDown = (e) => {
  if (isSpacePressed.value) {
    e.preventDefault();
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
  if (!container.value || (!e.ctrlKey && !e.metaKey)) return;
  e.preventDefault();
  const rect = container.value.getBoundingClientRect();
  const mouseX = e.clientX - rect.left;
  const mouseY = e.clientY - rect.top;
  const scaleFactor = e.deltaY > 0 ? 1 / 1.1 : 1.1;
  const newScale = Math.max(
    MIN_SCALE,
    Math.min(scale.value * scaleFactor, MAX_SCALE),
  );
  panX.value = mouseX - (mouseX - panX.value) * (newScale / scale.value);
  panY.value = mouseY - (mouseY - panY.value) * (newScale / scale.value);
  scale.value = newScale;
};
const zoomWithCenterFocus = (newScale) => {
  if (!container.value) return;
  const rect = container.value.getBoundingClientRect();
  const centerX = rect.width / 2;
  const centerY = rect.height / 2;
  panX.value = centerX - (centerX - panX.value) * (newScale / scale.value);
  panY.value = centerY - (centerY - panY.value) * (newScale / scale.value);
  scale.value = newScale;
};
const zoomIn = () => {
  const newScale = Math.min(scale.value * ZOOM_BUTTON_FACTOR, MAX_SCALE);
  zoomWithCenterFocus(newScale);
};
const zoomOut = () => {
  const newScale = Math.max(scale.value / ZOOM_BUTTON_FACTOR, MIN_SCALE);
  zoomWithCenterFocus(newScale);
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
    }, 1500);
  } catch (err) {
    console.error("Failed to copy diagram source:", err);
  }
};

// --- Lifecycle Hooks ---
onMounted(() => {
  initializeAndRender();

  window.addEventListener("mousemove", handleMouseMove);
  window.addEventListener("mouseup", handleMouseUp);
  if (container.value) {
    container.value.addEventListener("wheel", handleWheel, { passive: false });
  }

  const handleKeydown = (e) => {
    if (e.code === "Space") isSpacePressed.value = true;
  };
  const handleKeyup = (e) => {
    if (e.code === "Space") isSpacePressed.value = false;
  };
  window.addEventListener("keydown", handleKeydown);
  window.addEventListener("keyup", handleKeyup);

  // A simple re-render when visibility changes can help sync theme
  const handleVisibilityChange = () => {
    if (document.visibilityState === "visible") {
      initializeAndRender();
    }
  };
  document.addEventListener("visibilitychange", handleVisibilityChange);

  onUnmounted(() => {
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
    if (container.value) {
      container.value.removeEventListener("wheel", handleWheel);
    }
    window.removeEventListener("keydown", handleKeydown);
    window.removeEventListener("keyup", handleKeyup);
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  });
});

watch(
  () => props.diagramText,
  () => {
    initializeAndRender();
  },
);
</script>
