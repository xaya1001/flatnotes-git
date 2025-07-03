<template>
  <div
    data-mermaid-wrapper
    class="mermaid-diagram-container"
    :class="{
      'has-error': !!errorMessage,
      'is-fullscreen': isFullscreen,
    }"
  >
    <!-- Wrapper for overflow, panning, and zooming -->
    <div class="mermaid-scroll-wrapper">
      <div class="mermaid-render-target" :style="transformStyle">
        <!-- Error Box -->
        <div v-if="errorMessage" class="mermaid-error-box">
          <h4 class="mermaid-error-title">Mermaid Render Error</h4>
          <pre class="mermaid-error-text">{{ errorMessage }}</pre>
        </div>
        <!-- SVG Content -->
        <div
          v-else-if="svgContent"
          class="svg-wrapper"
          ref="svgWrapper"
          v-html="svgContent"
        ></div>
      </div>
    </div>

    <!-- Bottom-Right Controls: 3x3 Grid Layout -->
    <div v-if="!errorMessage" class="mermaid-controls-br">
      <div class="control-grid">
        <!-- Row 1 -->
        <button title="Copy Source" @click="copySource">
          <SvgIcon v-if="isCopied" type="mdi" :path="mdiCheck" :size="20" />
          <SvgIcon v-else type="mdi" :path="mdiContentCopy" :size="20" />
        </button>
        <button title="Pan Up" @click="pan('up')">
          <SvgIcon type="mdi" :path="mdiChevronUp" :size="20" />
        </button>
        <button title="Zoom In" @click="zoomIn">
          <SvgIcon type="mdi" :path="mdiMagnifyPlus" :size="20" />
        </button>

        <!-- Row 2 -->
        <button title="Pan Left" @click="pan('left')">
          <SvgIcon type="mdi" :path="mdiChevronLeft" :size="20" />
        </button>
        <button title="Reset View" @click="resetView">
          <SvgIcon type="mdi" :path="mdiRestore" :size="20" />
        </button>
        <button title="Pan Right" @click="pan('right')">
          <SvgIcon type="mdi" :path="mdiChevronRight" :size="20" />
        </button>

        <!-- Row 3 -->
        <button title="Toggle Fullscreen" @click="toggleFullscreen">
          <SvgIcon
            v-if="isFullscreen"
            type="mdi"
            :path="mdiFullscreenExit"
            :size="20"
          />
          <SvgIcon v-else type="mdi" :path="mdiFullscreen" :size="20" />
        </button>
        <button title="Pan Down" @click="pan('down')">
          <SvgIcon type="mdi" :path="mdiChevronDown" :size="20" />
        </button>
        <button title="Zoom Out" @click="zoomOut">
          <SvgIcon type="mdi" :path="mdiMagnifyMinus" :size="20" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import mermaid from "mermaid";
import SvgIcon from "@jamescoyle/vue-icon";
import {
  mdiChevronUp,
  mdiChevronDown,
  mdiChevronLeft,
  mdiChevronRight,
  mdiContentCopy,
  mdiMagnifyPlus,
  mdiMagnifyMinus,
  mdiRestore,
  mdiCheck,
  mdiFullscreen,
  mdiFullscreenExit,
} from "@mdi/js";

const props = defineProps({
  diagramText: { type: String, required: true },
});

// --- State Refs ---
const svgWrapper = ref(null);
const scale = ref(1);
const panX = ref(0);
const panY = ref(0);
const isCopied = ref(false);
const isFullscreen = ref(false);
const errorMessage = ref(null);
const svgContent = ref("");
let themeObserver = null;

const ZOOM_BUTTON_FACTOR = 1.25;
const PAN_STEP = 50;
const MAX_SCALE = 8;
const MIN_SCALE = 0.2;

const transformStyle = computed(() => {
  return `transform: translate(${panX.value}px, ${panY.value}px) scale(${scale.value});`;
});

const initializeAndRender = async (theme) => {
  if (!props.diagramText.trim()) return;
  errorMessage.value = null;
  svgContent.value = "";
  resetView();
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: theme,
    suppressErrorRendering: true,
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

const pan = (direction) => {
  switch (direction) {
    case "up":
      panY.value -= PAN_STEP;
      break;
    case "down":
      panY.value += PAN_STEP;
      break;
    case "left":
      panX.value -= PAN_STEP;
      break;
    case "right":
      panX.value += PAN_STEP;
      break;
  }
};

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
const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value;
};
const copySource = () => {
  if (isCopied.value) return;
  navigator.clipboard
    .writeText(props.diagramText)
    .then(() => {
      isCopied.value = true;
      setTimeout(() => {
        isCopied.value = false;
      }, 1500);
    })
    .catch((err) => {
      console.error("Failed to copy diagram source:", err);
    });
};

const handleEscKey = (e) => {
  if (e.key === "Escape" && isFullscreen.value) {
    isFullscreen.value = false;
  }
};

onMounted(() => {
  const initialTheme = document.body.classList.contains("dark")
    ? "dark"
    : "default";
  initializeAndRender(initialTheme);

  window.addEventListener("keydown", handleEscKey);

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
});

onUnmounted(() => {
  if (themeObserver) themeObserver.disconnect();
  window.removeEventListener("keydown", handleEscKey);
});

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
