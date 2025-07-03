<template>
  <div
    data-mermaid-wrapper
    class="mermaid-diagram-container"
    :class="{
      'has-error': !!errorMessage,
      'is-panning': isCtrlPressed,
    }"
    ref="container"
    @mousedown.prevent="handleMouseDown"
    @wheel.prevent="handleWheel"
  >
    <div class="mermaid-scroll-wrapper">
      <div class="mermaid-render-target" :style="transformStyle">
        <div v-if="errorMessage" class="mermaid-error-box">
          <h4 class="mermaid-error-title">Mermaid Render Error</h4>
          <pre class="mermaid-error-text">{{ errorMessage }}</pre>
        </div>
        <div
          v-else-if="svgContent"
          class="svg-wrapper"
          ref="svgWrapper"
          v-html="svgContent"
        ></div>
      </div>
    </div>

    <div v-if="!errorMessage" class="mermaid-controls">
      <button title="Copy Source" @click.stop="copySource" :disabled="isCopied">
        <SvgIcon v-if="isCopied" type="mdi" :path="mdiCheck" :size="18" />
        <SvgIcon v-else type="mdi" :path="mdiContentCopy" :size="18" />
      </button>
      <button title="Zoom In" @click.stop="zoomIn">
        <SvgIcon type="mdi" :path="mdiMagnifyPlus" :size="18" />
      </button>
      <button title="Zoom Out" @click.stop="zoomOut">
        <SvgIcon type="mdi" :path="mdiMagnifyMinus" :size="18" />
      </button>
      <button title="Reset View" @click.stop="resetView">
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

// Component State
const container = ref(null);
const svgWrapper = ref(null);
const scale = ref(1);
const panX = ref(0);
const panY = ref(0);
const isCtrlPressed = ref(false);
const isPanning = ref(false);
let panStart = { x: 0, y: 0 };
const isCopied = ref(false);
const errorMessage = ref(null);
const svgContent = ref("");
let themeObserver = null;

// Constants
const ZOOM_BUTTON_FACTOR = 1.25;
const MAX_SCALE = 8;
const MIN_SCALE = 0.2;

const transformStyle = computed(() => {
  return `transform: translate(${panX.value}px, ${panY.value}px) scale(${scale.value});`;
});

// Core Rendering Logic
const initializeAndRender = async () => {
  if (!props.diagramText.trim() || typeof document === "undefined") return;
  errorMessage.value = null;
  svgContent.value = "";
  resetView();
  const isDarkMode = document.body.classList.contains("dark");

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    suppressErrorRendering: true,
    fontFamily: '"Poppins", sans-serif',
    theme: isDarkMode ? "dark" : "default",
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

// Event Handlers for Pan & Zoom
const handleMouseDown = (e) => {
  if (e.ctrlKey || e.metaKey) {
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
  if (e.ctrlKey || e.metaKey) {
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
  }
};

// UI Control Actions
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
  zoomWithCenterFocus(Math.min(scale.value * ZOOM_BUTTON_FACTOR, MAX_SCALE));
};
const zoomOut = () => {
  zoomWithCenterFocus(Math.max(scale.value / ZOOM_BUTTON_FACTOR, MIN_SCALE));
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

// Lifecycle Hooks
onMounted(() => {
  initializeAndRender();

  window.addEventListener("mousemove", handleMouseMove);
  window.addEventListener("mouseup", handleMouseUp);

  const handleKeydown = (e) => {
    if (e.key === "Control" || e.key === "Meta") isCtrlPressed.value = true;
  };
  const handleKeyup = (e) => {
    if (e.key === "Control" || e.key === "Meta") {
      isCtrlPressed.value = false;
      isPanning.value = false;
    }
  };
  window.addEventListener("keydown", handleKeydown);
  window.addEventListener("keyup", handleKeyup);

  themeObserver = new MutationObserver(() => {
    initializeAndRender();
  });
  themeObserver.observe(document.body, {
    attributes: true,
    attributeFilter: ["class"],
  });

  onUnmounted(() => {
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
    window.removeEventListener("keydown", handleKeydown);
    window.removeEventListener("keyup", handleKeyup);
    if (themeObserver) themeObserver.disconnect();
  });
});

watch(() => props.diagramText, initializeAndRender);
</script>
