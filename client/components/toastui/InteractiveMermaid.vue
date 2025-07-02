<template>
  <div
    class="mermaid-diagram-container"
    :style="{ cursor: cursorStyle }"
    @mousedown="startPan"
    @mousemove="pan"
    @mouseup="endPan"
    @mouseleave="endPan"
    @wheel="zoom"
  >
    <div
      ref="svgContainer"
      class="mermaid-svg-container"
      :style="transformStyle"
    ></div>
    <div class="mermaid-controls">
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
  diagramText: {
    type: String,
    required: true,
  },
});

const svgContainer = ref(null);
const scale = ref(1);
const panX = ref(0);
const panY = ref(0);
const isPanning = ref(false);
const startX = ref(0);
const startY = ref(0);
const isCopied = ref(false);
const cursorStyle = ref("grab");
let themeObserver = null;

const ZOOM_BUTTON_FACTOR = 1.2;
const ZOOM_WHEEL_FACTOR = 1.1;

const transformStyle = computed(() => {
  return `transform: translate(${panX.value}px, ${panY.value}px) scale(${scale.value});`;
});

const initializeAndRender = async (theme) => {
  if (!svgContainer.value || !props.diagramText.trim()) return;

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: theme,
  });

  svgContainer.value.innerHTML = ""; // Clean previous render
  const mermaidInternalId = `d${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

  try {
    const { svg } = await mermaid.render(mermaidInternalId, props.diagramText);
    svgContainer.value.innerHTML = svg;
  } catch (error) {
    console.error("Failed to render Mermaid diagram:", error);
    const errorContainer = document.createElement("div");
    errorContainer.className = "mermaid-error-box";
    errorContainer.textContent = `Error rendering Mermaid diagram: ${error.message}`;
    svgContainer.value.appendChild(errorContainer);
  }
};

const handleThemeChange = (newTheme) => {
  initializeAndRender(newTheme);
};

onMounted(() => {
  const initialTheme = document.body.classList.contains("dark")
    ? "dark"
    : "default";
  initializeAndRender(initialTheme);

  // Set up the observer to watch for theme changes on the body
  themeObserver = new MutationObserver((mutationsList) => {
    for (const mutation of mutationsList) {
      if (
        mutation.type === "attributes" &&
        mutation.attributeName === "class"
      ) {
        const newTheme = document.body.classList.contains("dark")
          ? "dark"
          : "default";
        handleThemeChange(newTheme);
      }
    }
  });

  themeObserver.observe(document.body, { attributes: true });
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

onUnmounted(() => {
  if (themeObserver) {
    themeObserver.disconnect();
  }
});

// --- User Interaction functions ---
const startPan = (e) => {
  if (e.target.closest(".mermaid-controls")) return;
  e.preventDefault();
  isPanning.value = true;
  startX.value = e.clientX - panX.value;
  startY.value = e.clientY - panY.value;
  cursorStyle.value = "grabbing";
};

const pan = (e) => {
  if (isPanning.value) {
    panX.value = e.clientX - startX.value;
    panY.value = e.clientY - startY.value;
  }
};

const endPan = (e) => {
  isPanning.value = false;
  cursorStyle.value = "grab";
};

const zoom = (e) => {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault();
    const scaleAmount =
      e.deltaY > 0 ? 1 / ZOOM_WHEEL_FACTOR : ZOOM_WHEEL_FACTOR;
    scale.value *= scaleAmount;
  }
};

const zoomIn = () => {
  scale.value *= ZOOM_BUTTON_FACTOR;
};

const zoomOut = () => {
  scale.value /= ZOOM_BUTTON_FACTOR;
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
</script>
