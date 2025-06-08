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

      <!-- GIT PANEL INTEGRATION -->
      <GitStatusIndicator
        v-if="gitIntegrationEnabled"
        @toggle-panel="handleToggleGitPanel"
      />

      <div
        v-if="isGitPanelVisible && gitIntegrationEnabled"
        @mousedown="handlePanelOverlayMouseDown"
        @mouseup="handlePanelOverlayMouseUp"
        class="fixed inset-0 z-40"
      >
        <div class="absolute right-5 top-20 w-full max-w-md md:max-w-lg">
          <GitPanel @close="closeGitPanel" @pin-toggled="pinToggled" />
        </div>
      </div>
    </template>

    <div v-else class="flex flex-grow items-center justify-center">
      <p class="text-theme-text-muted">Loading application...</p>
    </div>
  </LoadingIndicator>
</template>

<script setup>
import Mousetrap from 'mousetrap';
import 'mousetrap/plugins/global-bind/mousetrap-global-bind';
import { useToast } from 'primevue/usetoast';
import { computed, ref, onMounted } from 'vue';
import { RouterView, useRoute } from 'vue-router';

import { apiErrorHandler, getConfig } from './api.js';
import PrimeToast from './components/PrimeToast.vue';
import ConfirmDialog from 'primevue/confirmdialog';
import { useGlobalStore } from './globalStore.js';
import { loadTheme } from './helpers.js';
import NavBar from './partials/NavBar.vue';
import SearchModal from './partials/SearchModal.vue';
import { loadStoredToken } from './tokenStorage.js';
import LoadingIndicator from './components/LoadingIndicator.vue';
import GitPanel from './components/GitPanel.vue';
import GitStatusIndicator from './components/GitStatusIndicator.vue';
import router from './router.js';

const globalStore = useGlobalStore();
const isSearchModalVisible = ref(false);
const loadingIndicator = ref();
const navBar = ref();
const route = useRoute();
const toast = useToast();

const isConfigLoaded = ref(false);

const isGitPanelVisible = ref(false);
const isGitPanelPinned = ref(false);
const gitIntegrationEnabled = computed(
  () => globalStore.config.value?.flatnotesGitEnabled
);

let isMouseDownOnOverlay = false;

// '/' to search
Mousetrap.bind('/', () => {
  if (route.name !== 'login') {
    toggleSearchModal();
    return false;
  }
});

// 'CTRL + ALT/OPT + N' to create new note
Mousetrap.bindGlobal('ctrl+alt+n', () => {
  if (route.name !== 'login') {
    router.push({ name: 'new' });
    return false;
  }
});

// 'CTRL + ALT/OPT + H' to go to home
Mousetrap.bindGlobal('ctrl+alt+h', () => {
  if (route.name !== 'login') {
    router.push({ name: 'home' });
    return false;
  }
});

onMounted(() => {
  getConfig()
    .then((data) => {
      globalStore.config.value = data;

      isConfigLoaded.value = true;

      loadingIndicator.value.setLoaded();
    })
    .catch((error) => {
      apiErrorHandler(error, toast);
      loadingIndicator.value.setFailed();
    });

  loadStoredToken();
  loadTheme();
});

const showNavBar = computed(() => {
  return route.name !== 'login';
});

const showNavBarLogo = computed(() => {
  return route.name !== 'home';
});

function toggleSearchModal() {
  isSearchModalVisible.value = !isSearchModalVisible.value;
}

function handleToggleGitPanel() {
  isGitPanelVisible.value = !isGitPanelVisible.value;
}

function closeGitPanel() {
  isGitPanelVisible.value = false;
}

function pinToggled(isPinned) {
  isGitPanelPinned.value = isPinned;
}

function handlePanelOverlayMouseDown(event) {
  // If the panel is pinned, do nothing.
  if (isGitPanelPinned.value) return;

  // Only register mousedown if it's on the overlay itself, not the panel.
  if (event.target === event.currentTarget) {
    // CORRECTED: Assign to the boolean variable directly.
    isMouseDownOnOverlay = true;
  }
}

function handlePanelOverlayMouseUp(event) {
  // If the panel is pinned, do nothing.
  if (isGitPanelPinned.value) return;

  // Close only if mousedown and mouseup were on the overlay.
  if (event.target === event.currentTarget && isMouseDownOnOverlay) {
    closeGitPanel();
  }
  // CORRECTED: Reset the boolean variable directly.
  isMouseDownOnOverlay = false;
}
</script>
