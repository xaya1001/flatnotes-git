<template>
  <LoadingIndicator
    ref="loadingIndicator"
    class="container mx-auto px-2 py-4 print:max-w-full"
  >
    <PrimeToast />
    <ConfirmDialog />
    <SearchModal v-model="isSearchModalVisible" />

    <!-- The fixed NavBar -->
    <div
      v-if="showNavBar"
      class="fixed left-0 right-0 top-0 z-20 h-20 bg-theme-background"
    >
      <div class="container mx-auto h-full px-2 py-3">
        <NavBar
          ref="navBar"
          :class="{ 'print:hidden': route.name == 'note' }"
          class="h-full"
          :hide-logo="!showNavBarLogo"
          @toggleSearchModal="toggleSearchModal"
        />
      </div>
    </div>

    <template v-if="isConfigLoaded">
      <div>
        <RouterView :key="route.fullPath" />
      </div>
      <GitSidebar v-if="gitIntegrationEnabled" />
    </template>
    <div v-else class="flex h-screen flex-grow items-center justify-center">
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
import router from "./router.js";
import ConfirmDialog from "primevue/confirmdialog";
import GitSidebar from "./git-integration/components/GitSidebar.vue";
import { useGitIntegration } from "./git-integration/composables/useGitIntegration.js";

const globalStore = useGlobalStore();
const isSearchModalVisible = ref(false);
const loadingIndicator = ref();
const navBar = ref();
const route = useRoute();
const toast = useToast();

const isConfigLoaded = ref(false);
const gitIntegrationEnabled = computed(
  () => globalStore.config.value?.flatnotesGitEnabled,
);
useGitIntegration();

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

const showNavBar = computed(() => route.name !== "login");
const showNavBarLogo = computed(() => route.name !== "home");

function toggleSearchModal() {
  isSearchModalVisible.value = !isSearchModalVisible.value;
}
</script>
