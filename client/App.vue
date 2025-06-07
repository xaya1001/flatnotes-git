<template>
  <LoadingIndicator
    ref="loadingIndicator"
    class="container mx-auto flex h-screen flex-col px-2 py-4 print:max-w-full"
  >
    <PrimeToast />
    <SearchModal v-model="isSearchModalVisible" />   
    <template v-if="isConfigLoaded">
      <NavBar
        v-if="showNavBar"
        ref="navBar"
        :class="{ 'print:hidden': route.name == 'note' }"
        :hide-logo="!showNavBarLogo"
        @toggleSearchModal="toggleSearchModal"
        @toggleGitPanel="handleToggleGitPanel"
      />
      <RouterView />

      <!-- GIT PANEL INTEGRATION -->
      <div v-if="isGitPanelVisible && gitIntegrationEnabled" 
           class="fixed bottom-0 right-0 mb-4 mr-4 z-40 w-full max-w-md md:max-w-lg max-h-[70vh] overflow-y-auto">
        <GitPanel @close="isGitPanelVisible = false" />
      </div>
    </template>
    
    <div v-else class="flex-grow flex items-center justify-center">
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
import { useGlobalStore } from "./globalStore.js";
import { loadTheme } from "./helpers.js";
import NavBar from "./partials/NavBar.vue";
import SearchModal from "./partials/SearchModal.vue";
import { loadStoredToken } from "./tokenStorage.js";
import LoadingIndicator from "./components/LoadingIndicator.vue";
import GitPanel from "./components/GitPanel.vue";
import router from "./router.js";

const globalStore = useGlobalStore();
const isSearchModalVisible = ref(false);
const loadingIndicator = ref();
const navBar = ref();
const route = useRoute();
const toast = useToast();

const isConfigLoaded = ref(false);

const isGitPanelVisible = ref(false);
const gitIntegrationEnabled = computed(() => globalStore.config.value?.flatnotesGitEnabled);

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

function handleToggleGitPanel() {
  if (gitIntegrationEnabled.value) {
    isGitPanelVisible.value = !isGitPanelVisible.value;
  }
}
</script>
