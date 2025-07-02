<template>
  <div
    data-mermaid-wrapper
    class="mermaid-diagram-container"
    :class="{ 'has-error': !!errorMessage }"
  >
    <!-- wrapper for native scrolling -->
    <div ref="scrollWrapper" class="mermaid-scroll-wrapper" @wheel="zoom">
      <!-- The target where the SVG or error message will be rendered -->
      <div
        ref="renderTarget"
        class="mermaid-render-target"
        :style="transformStyle"
      >
        <!-- Use v-if/v-else-if for fully declarative rendering -->
        <pre v-if="errorMessage" class="mermaid-error-text">{{
          errorMessage
        }}</pre>
        <div
          v-else-if="svgContent"
          class="svg-wrapper"
          v-html="svgContent"
        ></div>
      </div>
    </div>

    <!-- Controls are positioned relative to the main container, outside the scroll wrapper -->
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
const scrollWrapper = ref(null);
const scale = ref(1);
const isCopied = ref(false);
const errorMessage = ref(null);
const svgContent = ref("");
let themeObserver = null;

const ZOOM_BUTTON_FACTOR = 1.2;
const ZOOM_WHEEL_FACTOR = 1.1;

const transformStyle = computed(() => {
  return `transform: scale(${scale.value}); transform-origin: center;`;
});

const initializeAndRender = async (theme) => {
  if (!renderTarget.value || !props.diagramText.trim()) return;

  // Reset state refs
  errorMessage.value = null;
  svgContent.value = "";

  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: theme,
  });

  const mermaidInternalId = `d${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;

  let tempContainer = null;
  try {
    tempContainer = document.createElement("div");
    tempContainer.style.position = "absolute";
    tempContainer.style.left = "-9999px";
    tempContainer.style.top = "-9999px";
    document.body.appendChild(tempContainer);

    const { svg } = await mermaid.render(
      mermaidInternalId,
      props.diagramText,
      tempContainer,
    );
    // On success, update the state ref. Let Vue handle the DOM.
    svgContent.value = svg;
  } catch (error) {
    console.error("Failed to render Mermaid diagram:", error);
    // On failure, update the error state ref.
    errorMessage.value = error.message;
  } finally {
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
  if (scrollWrapper.value) {
    scrollWrapper.value.scrollTop = 0;
    scrollWrapper.value.scrollLeft = 0;
  }
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
