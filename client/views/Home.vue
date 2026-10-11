<template>
  <div class="flex h-full justify-center">
    <div class="flex max-w-[500px] flex-1 flex-col items-center pt-[25vh]">
      <Logo class="mb-5" />
      <SearchInput class="mb-5 shadow-[0_0_20px] shadow-theme-shadow" />
      <LoadingIndicator
        ref="loadingIndicator"
        class="flex min-h-56 flex-col items-center"
        hideLoader
      >
        <p
          v-if="notes.length > 0 && globalStore.config.value"
          class="mb-2 text-xs font-bold uppercase text-theme-text-very-muted"
        >
          {{ globalStore.config.value.quickAccessTitle }}
        </p>
        <RouterLink
          v-for="note in notes.slice(0, globalStore.config.value?.quickAccessLimit)"
          :key="note.title"
          :to="{ name: 'note', params: { title: note.title } }"
          class="mb-1"
        >
          <CustomButton :label="note.title" />
        </RouterLink>
        <RouterLink
          v-if="globalStore.config.value && notes.length > globalStore.config.value.quickAccessLimit"
          :to="{
            name: 'search',
            query: {
              term: globalStore.config.value.quickAccessTerm,
              sortBy: searchSortOptions[globalStore.config.value.quickAccessSort],
            },
          }"
          title="Show more"
          ><CustomButton :iconPath="mdiDotsHorizontal"
        /></RouterLink>
      </LoadingIndicator>
    </div>
  </div>
</template>

<script setup>
import { mdiDotsHorizontal } from "@mdi/js";
import { useToast } from "primevue/usetoast";
import { ref, watch } from "vue"; 
import { RouterLink } from "vue-router";

import { apiErrorHandler, getNotes } from "../api.js";
import CustomButton from "../components/CustomButton.vue";
import LoadingIndicator from "../components/LoadingIndicator.vue";
import Logo from "../components/Logo.vue";
import { searchSortOptions } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import SearchInput from "../partials/SearchInput.vue";

const globalStore = useGlobalStore();
const loadingIndicator = ref();
const notes = ref([]);
const toast = useToast();

function init() {
  if (!globalStore.config.value?.authType || globalStore.config.value.quickAccessHide) {
    loadingIndicator.value.setLoaded(); 
    return;
  }
  
  const limit = Number(globalStore.config.value.quickAccessLimit);
  if (isNaN(limit)) {
      console.error("quickAccessLimit is not a number, aborting init.");
      loadingIndicator.value.setFailed();
      return;
  }

  getNotes(
    globalStore.config.value.quickAccessTerm,
    globalStore.config.value.quickAccessSort,
    // Order by ascending if sorting by title, descending otherwise.
    globalStore.config.value.quickAccessSort === "title"
      ? "asc"
      : "desc",
    // Limit is increased by 1 to check if there are more notes than the limit.
    limit + 1,
  )
    .then((data) => {
      notes.value = data;
      loadingIndicator.value.setLoaded();
    })
    .catch((error) => {
      loadingIndicator.value.setFailed();
      apiErrorHandler(error, toast);
    });
}

// Watch for the config object to be populated. 
watch(
  () => globalStore.config.value?.authType, 
  (newValue, oldValue) => {
    if (newValue && !oldValue) {
      init();
    }
  },
  { immediate: true } 
);

</script>
