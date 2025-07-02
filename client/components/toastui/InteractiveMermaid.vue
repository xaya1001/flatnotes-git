<template>
  <div
    data-mermaid-wrapper
    class="mermaid-diagram-container"
    :class="{ 'has-error': !!errorMessage }"
    :style="{ cursor: cursorStyle }"
    @mousedown="startPan"
    @mousemove="pan"
    @mouseup="endPan"
    @mouseleave="endPan"
    @wheel="zoom"
  >
    <!-- This container will hold either the SVG or the error message -->
    <div
      ref="renderTarget"
      class="mermaid-render-target"
      :style="transformStyle"
    ></div>

    <!-- Controls are only shown when there is NO error -->
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
  diagramText: {
    type: String,
    required: true,
  },
});

const renderTarget = ref(null);
const scale = ref(1);
const panX = ref(0);
const panY = ref(0);
const isPanning = ref(false);
const startX = ref(0);
const startY = ref(0);
const isCopied = ref(false);
const errorMessage = ref(null);
let themeObserver = null;

const ZOOM_BUTTON_FACTOR = 1.2;
const ZOOM_WHEEL_FACTOR = 1.1;

const transformStyle = computed(() => {
  if (errorMessage.value) {
    return "transform: none;";
  }
  return `transform: translate(${panX.value}px, ${panY.value}px) scale(${scale.value});`;
});

const cursorStyle = computed(() => {
  if (errorMessage.value) return "default";
  return isPanning.value ? "grabbing" : "grab";
});

const initializeAndRender = async (theme) => {
  if (!renderTarget.value || !props.diagramText.trim()) return;

  errorMessage.value = null;
  renderTarget.value.innerHTML = "";

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: theme,
  });

  const mermaidInternalId = `d${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

  // FINAL, ROBUST FIX: Use a temporary, off-screen element for rendering.
  let tempContainer = null;
  try {
    // 1. Create a temporary 'stage' and hide it off-screen
    tempContainer = document.createElement("div");
    tempContainer.style.position = "absolute";
    tempContainer.style.left = "-9999px";
    tempContainer.style.top = "-9999px";
    document.body.appendChild(tempContainer);

    // 2. Let Mermaid render into this valid, but invisible, DOM node
    const { svg } = await mermaid.render(
      mermaidInternalId,
      props.diagramText,
      tempContainer,
    );

    // 3. If successful, copy the clean SVG to our visible target
    renderTarget.value.innerHTML = svg;
  } catch (error) {
    // 4. If it fails, the bomb SVG is contained in the temp container.
    // We only display the clean text error message.
    console.error("Failed to render Mermaid diagram:", error);
    errorMessage.value = error.message;

    const pre = document.createElement("pre");
    pre.className = "mermaid-error-text";
    pre.textContent = errorMessage.value;
    renderTarget.value.appendChild(pre);
  } finally {
    // 5. CRITICAL: Always remove the temporary stage from the DOM
    if (tempContainer && document.body.contains(tempContainer)) {
      document.body.removeChild(tempContainer);
    }
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

const startPan = (e) => {
  if (errorMessage.value || e.target.closest(".mermaid-controls")) return;
  e.preventDefault();
  isPanning.value = true;
  startX.value = e.clientX - panX.value;
  startY.value = e.clientY - panY.value;
};

const pan = (e) => {
  if (errorMessage.value || !isPanning.value) return;
  panX.value = e.clientX - startX.value;
  panY.value = e.clientY - startY.value;
};

const endPan = () => {
  if (errorMessage.value) return;
  isPanning.value = false;
};

const zoom = (e) => {
  if (errorMessage.value || (!e.ctrlKey && !e.metaKey)) return;
  e.preventDefault();
  const scaleAmount = e.deltaY > 0 ? 1 / ZOOM_WHEEL_FACTOR : ZOOM_WHEEL_FACTOR;
  scale.value *= scaleAmount;
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
