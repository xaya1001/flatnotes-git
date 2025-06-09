<template>
  <div
    v-if="gitIntegrationEnabled"
    class="git-panel flex flex-col rounded-lg border bg-theme-background-elevated text-theme-text shadow-2xl"
  >
    <!-- Panel Header -->
    <div
      class="flex flex-shrink-0 items-center justify-between border-b border-theme-border p-3"
    >
      <div class="flex items-center space-x-2">
        <h2 class="text-lg font-semibold">Git Sync</h2>
        <button
          @click="store.refreshAll"
          class="rounded-full p-1 hover:bg-theme-border"
          title="Refresh"
        >
          <SvgIcon
            type="mdi"
            :path="mdilRefresh"
            :size="20"
            :class="{ 'animate-spin': store.isRefreshing }"
          />
        </button>
      </div>
      <div class="flex items-center space-x-1">
        <button
          @click="handlePinClick"
          class="rounded-full p-1 hover:bg-theme-border"
          :title="store.isPinned ? 'Unpin Panel' : 'Pin Panel'"
        >
          <SvgIcon
            type="mdi"
            :path="store.isPinned ? mdilPin : mdilPinOff"
            :size="20"
          />
        </button>
        <button
          @click="$emit('close')"
          class="rounded-full p-1 hover:bg-theme-border"
          title="Close (Esc)"
        >
          <SvgIcon type="mdi" :path="mdiClose" :size="20" />
        </button>
      </div>
    </div>

    <!-- Confirmation Modal -->
    <ConfirmModal
      v-model="store.isConfirmModalVisible"
      :title="store.confirmModalProps.title"
      :message="store.confirmModalProps.message"
      :confirmButtonText="store.confirmModalProps.confirmButtonText"
      :confirmButtonStyle="store.confirmModalProps.confirmButtonStyle"
      @confirm="() => store.resolveConfirmation(true)"
      @cancel="() => store.resolveConfirmation(false)"
      @reject="() => store.resolveConfirmation(false)"
    />

    <!-- TabView orchestrating the smart tabs -->
    <TabView
      class="flex min-h-0 flex-grow flex-col"
      :pt="{ panelContainer: { class: 'flex-grow min-h-0 overflow-hidden' } }"
    >
      <TabPanel
        header="Changes"
        :pt="{ content: { class: 'p-0 flex flex-col h-full' } }"
      >
        <GitChangesTab />
      </TabPanel>

      <TabPanel
        header="History"
        :pt="{ content: { class: 'p-0 flex flex-col h-full' } }"
      >
        <GitHistoryTab />
      </TabPanel>

      <TabPanel
        header="Actions"
        :pt="{ content: { class: 'p-0 flex flex-col h-full' } }"
      >
        <GitActionsTab />
      </TabPanel>

      <TabPanel
        header="Log"
        :pt="{ content: { class: 'p-0 flex flex-col h-full' } }"
      >
        <GitLogTab />
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from "vue";
import { useGlobalStore } from "../globalStore";
import { useGitStore } from "../gitStore";

// Icons
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilRefresh, mdilPin, mdilPinOff } from "@mdi/light-js";
import { mdiClose } from "@mdi/js";

// PrimeVue & Custom Components
import ConfirmModal from "./ConfirmModal.vue";
import TabView from "primevue/tabview";
import TabPanel from "primevue/tabpanel";
import GitChangesTab from "./GitPanel/GitChangesTab.vue";
import GitHistoryTab from "./GitPanel/GitHistoryTab.vue";
import GitActionsTab from "./GitPanel/GitActionsTab.vue";
import GitLogTab from "./GitPanel/GitLogTab.vue";

const emit = defineEmits(["close", "pin-toggled"]);

const globalStore = useGlobalStore();
const store = useGitStore();

const gitIntegrationEnabled = computed(
  () => globalStore.config.value?.flatnotesGitEnabled,
);

function handlePinClick() {
  store.togglePin();
  emit("pin-toggled", store.isPinned);
}

onMounted(() => {
  if (gitIntegrationEnabled.value) {
    store.initialize();
  }
});

onUnmounted(() => {
  store.cleanup();
});
</script>

<style scoped>
.git-panel {
  height: 85vh;
}
:deep([data-pc-section="nav"]) {
  @apply flex flex-shrink-0 border-b border-theme-border px-2;
}
:deep([data-pc-section="header"]) {
  @apply mr-2;
}
:deep([data-pc-section="headeraction"]) {
  @apply block cursor-pointer border-b-2 border-transparent px-2 py-3 text-sm font-semibold text-theme-text-muted transition-colors duration-200 hover:text-theme-text focus:outline-none;
}
:deep([data-p-highlight="true"] > [data-pc-section="headeraction"]) {
  @apply border-theme-brand text-theme-brand;
}
:deep([data-pc-section="inkbar"]) {
  @apply hidden;
}
:deep(.p-datatable .p-datatable-thead > tr > th) {
  @apply border-b border-theme-border bg-theme-background-elevated px-2 py-3 text-left text-xs font-semibold uppercase text-theme-text-muted;
}
:deep(.p-datatable .p-datatable-tbody > tr) {
  @apply bg-transparent text-theme-text;
}
:deep(.p-datatable .p-datatable-tbody > tr > td) {
  @apply border-0 border-b border-theme-border px-2 py-2 text-sm;
}
</style>
