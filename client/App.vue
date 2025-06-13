<template>
  <LoadingIndicator
    ref="loadingIndicator"
    class="container mx-auto flex h-screen flex-col px-2 py-4 print:max-w-full"
  >
    <PrimeToast />
    <ConfirmDialog />
    <SearchModal v-model="isSearchModalVisible" />
    <template v-if="isConfigLoaded">
      <NavBar
        v-if="showNavBar"
        ref="navBar"
        :class="{ 'print:hidden': route.name == 'note' }"
        :hide-logo="!showNavBarLogo"
        @toggleSearchModal="toggleSearchModal"
      />
      <RouterView />
      <!-- BEGIN: Git Panel Integration -->
      <GitStatusIndicator
        v-if="gitIntegrationEnabled"
        @toggle-panel="panelUiStore.toggleVisibility"
      />
      <div
        v-if="panelUiStore.isVisible && gitIntegrationEnabled"
        @mousedown="handlePanelOverlayMouseDown"
        @mouseup="handlePanelOverlayMouseUp"
        class="fixed inset-0 z-40"
      >
        <div class="absolute right-5 top-20 w-full max-w-md md:max-w-lg">
          <GitPanel
            @close="panelUiStore.hidePanel"
            @pin-toggled="panelUiStore.isPinned = $event"
          />
        </div>
      </div>
      <!-- END: Git Panel Integration -->
    </template>
    <div v-else class="flex flex-grow items-center justify-center">
      <p class="text-theme-text-muted">Loading application...</p>
    </div>
  </LoadingIndicator>
</template>

<script setup>
import Mousetrap from "mousetrap";
import "mousetrap/plugins/global-bind/mousetrap-global-bind";
import { useToast } from "primevue/usetoast";
import { computed, ref, onMounted } from "vue";
import { RouterView, useRoute } from "vue-router";

import { apiErrorHandler, getConfig } from "./api.js";
import PrimeToast from "./components/PrimeToast.vue";
import ConfirmDialog from "primevue/confirmdialog";
import { useGlobalStore } from "./globalStore.js";
import { loadTheme } from "./helpers.js";
import NavBar from "./partials/NavBar.vue";
import SearchModal from "./partials/SearchModal.vue";
import { loadStoredToken } from "./tokenStorage.js";
import LoadingIndicator from "./components/LoadingIndicator.vue";
import router from "./router.js";

// BEGIN: Git Panel Integration Imports
import GitPanel from "./git-integration/components/GitPanel.vue";
import GitStatusIndicator from "./git-integration/components/GitStatusIndicator.vue";
import { useStatusStore } from "./git-integration/stores/statusStore.js";
import { usePanelUiStore } from "./git-integration/stores/panelUiStore.js";
// END: Git Panel Integration Imports

const globalStore = useGlobalStore();
const isSearchModalVisible = ref(false);
const loadingIndicator = ref();
const navBar = ref();
const route = useRoute();
const toast = useToast();
const isConfigLoaded = ref(false);

const statusStore = useStatusStore();
const panelUiStore = usePanelUiStore();

const gitIntegrationEnabled = computed(
  () => globalStore.config.value?.flatnotesGitEnabled,
);

let isMouseDownOnOverlay = false;

// '/' to search
Mousetrap.bind("/", () => {
  if (route.name !== "login") {
    toggleSearchModal();
    return false;
  }
});

// 'CTRL + ALT/OPT + N' to create new note
Mousetrap.bindGlobal("ctrl+alt+n", () => {
  if (route.name !== "login") {
    router.push({ name: "new" });
    return false;
  }
});

// 'CTRL + ALT/OPT + H' to go to home
Mousetrap.bindGlobal("ctrl+alt+h", () => {
  if (route.name !== "login") {
    router.push({ name: "home" });
    return false;
  }
});

onMounted(() => {
  getConfig()
    .then((data) => {
      globalStore.config.value = data;
      isConfigLoaded.value = true;
      loadingIndicator.value.setLoaded();
      if (data.flatnotesGitEnabled) {
        statusStore.initialize();
      }
    })
    .catch((error) => {
      apiErrorHandler(error, toast);
      loadingIndicator.value.setFailed();
    });

  loadStoredToken();
  loadTheme();
});

const showNavBar = computed(() => {
  return route.name !== "login";
});

const showNavBarLogo = computed(() => {
  return route.name !== "home";
});

function toggleSearchModal() {
  isSearchModalVisible.value = !isSearchModalVisible.value;
}

function handlePanelOverlayMouseDown(event) {
  if (panelUiStore.isPinned) return;
  if (event.target === event.currentTarget) {
    isMouseDownOnOverlay = true;
  }
}

function handlePanelOverlayMouseUp(event) {
  if (panelUiStore.isPinned) return;
  if (event.target === event.currentTarget && isMouseDownOnOverlay) {
    panelUiStore.hidePanel();
  }
  isMouseDownOnOverlay = false;
}
</script>
