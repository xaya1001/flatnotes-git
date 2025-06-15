<!-- client/git-integration/components/GitSidebar.vue -->
<template>
  <div class="fixed right-0 top-0 z-40 h-full">
    <!-- Sidebar Component -->
    <Sidebar
      v-model:visible="panelUiStore.isSidebarVisible"
      position="right"
      :modal="!panelUiStore.isPinned"
      :dismissable="!panelUiStore.isPinned"
      :showCloseIcon="false"
      @hide="panelUiStore.hideSidebar"
      :pt="{
        root: {
          class:
            'h-full border-l border-theme-border bg-theme-background-elevated shadow-none flex flex-col w-[480px]',
        },
        content: { class: 'p-0 h-full flex-grow min-h-0' },
      }"
    >
      <div class="flex h-full flex-col">
        <!-- Header -->
        <div
          class="flex flex-shrink-0 items-center justify-between border-b border-theme-border p-3"
        >
          <div class="flex flex-shrink-0 items-center space-x-2">
            <h2 class="text-lg font-semibold">Git Sync</h2>
            <button
              @click="refreshAll"
              class="rounded-full p-1 hover:bg-theme-border"
              title="Refresh"
            >
              <SvgIcon
                type="mdi"
                :path="mdilRefresh"
                :size="20"
                :class="{ 'animate-spin': isRefreshing }"
              />
            </button>
          </div>
          <div
            class="flex flex-grow items-center justify-center space-x-2 text-xs text-theme-text-muted"
          >
            <template v-if="globalConfig?.flatnotesGitAutoSyncInterval > 0">
              <span>
                Auto Sync (every
                {{ globalConfig.flatnotesGitAutoSyncInterval }} min)
              </span>
              <Toggle
                :isOn="!actionsStore.isAutoSyncPaused"
                :label="actionsStore.isAutoSyncPaused ? 'Paused' : 'Enabled'"
                @click="actionsStore.toggleAutoSyncPause"
                :disabled="actionsStore.isActionLoading"
              />
            </template>
            <span v-else>Automatic Sync Disabled</span>
          </div>
          <div class="flex flex-shrink-0 items-center space-x-1">
            <button
              @click="panelUiStore.togglePin()"
              class="rounded-full p-1 hover:bg-theme-border"
              :title="panelUiStore.isPinned ? 'Unpin Panel' : 'Pin Panel'"
            >
              <SvgIcon
                type="mdi"
                :path="panelUiStore.isPinned ? mdilPin : mdilPinOff"
                :size="20"
              />
            </button>
          </div>
        </div>

        <!-- Confirmation Modal -->
        <ConfirmModal
          v-model="panelUiStore.isConfirmModalVisible"
          :title="panelUiStore.confirmModalProps.title"
          :message="panelUiStore.confirmModalProps.message"
          :confirmButtonText="panelUiStore.confirmModalProps.confirmButtonText"
          :confirmButtonStyle="
            panelUiStore.confirmModalProps.confirmButtonStyle
          "
          @confirm="() => panelUiStore.resolveConfirmation(true)"
          @cancel="() => panelUiStore.resolveConfirmation(false)"
          @reject="() => panelUiStore.resolveConfirmation(false)"
        />

        <!-- Main TabView with 3 Tabs -->
        <TabView
          class="main-tabview flex min-h-0 flex-grow flex-col"
          :pt="{
            panelContainer: { class: 'flex-grow min-h-0 overflow-hidden' },
            nav: { class: 'main-tabview-nav' },
          }"
        >
          <TabPanel
            header="Workspace"
            :pt="{ content: { class: 'p-0 flex flex-col h-full' } }"
          >
            <WorkspaceTab />
          </TabPanel>
          <TabPanel
            header="History"
            :pt="{ content: { class: 'p-0 flex flex-col h-full' } }"
          >
            <GitHistoryTab />
          </TabPanel>
          <TabPanel header="Log" :pt="{ content: { class: 'p-0 h-full' } }">
            <GitLogTab />
          </TabPanel>
        </TabView>
      </div>
    </Sidebar>

    <!-- Toggle Indicator -->
    <GitStatusIndicator @toggle-sidebar="panelUiStore.toggleSidebar" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import Sidebar from "primevue/sidebar";
import TabView from "primevue/tabview";
import TabPanel from "primevue/tabpanel";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilRefresh, mdilPin, mdilPinOff } from "@mdi/light-js";

import { useGlobalStore } from "../../globalStore";
import { usePanelUiStore } from "../stores/panelUiStore";
import { useStatusStore } from "../stores/statusStore";
import { useHistoryStore } from "../stores/historyStore";
import { useActionsStore } from "../stores/actionsStore";
import { useLogStore } from "../stores/logStore";

import GitStatusIndicator from "./GitStatusIndicator.vue";
import ConfirmModal from "../../components/ConfirmModal.vue";
import Toggle from "../../components/Toggle.vue";
import WorkspaceTab from "./tabs/WorkspaceTab.vue";
import GitLogTab from "./tabs/GitLogTab.vue";
import GitHistoryTab from "./tabs/GitHistoryTab.vue";

const globalStore = useGlobalStore();
const panelUiStore = usePanelUiStore();
const statusStore = useStatusStore();
const historyStore = useHistoryStore();
const actionsStore = useActionsStore();
const logStore = useLogStore();

const isRefreshing = ref(false);
const globalConfig = computed(() => globalStore.config.value);

async function refreshAll() {
  isRefreshing.value = true;
  const pendingLogId = logStore.addPendingLog("Refreshing all data...");
  await Promise.all([
    statusStore.fetchStatus(),
    historyStore.fetchGitLog(),
    logStore.fetchActivityLog(),
  ]);
  logStore.updateLog(pendingLogId, {
    level: "success",
    message: "All data refreshed.",
    details: null,
  });
  isRefreshing.value = false;
}

onMounted(() => {
  if (globalConfig.value?.flatnotesGitEnabled) {
    logStore.initialize();
    historyStore.fetchGitLog();
    if (globalConfig.value.flatnotesGitAutoSyncInterval > 0) {
      actionsStore.fetchAutoSyncState();
    }
  }
});

onUnmounted(() => {
  if (globalConfig.value?.flatnotesGitEnabled) {
    statusStore.cleanup();
    logStore.cleanup();
  }
});
</script>

<style scoped>
/* PrimeVue sidebar custom styling */
.p-sidebar {
  transition: transform 0.3s;
}
.p-sidebar-right.p-sidebar-enter-from,
.p-sidebar-right.p-sidebar-leave-to {
  transform: translateX(100%);
}

/* --- Main TabView Styling (Final Version Based on User Feedback) --- */
:deep(.main-tabview .main-tabview-nav) {
  @apply flex flex-row justify-center border-b border-theme-border;
}
:deep(.main-tabview [role="tablist"]) {
  @apply flex flex-row justify-center border-b border-theme-border;
}
:deep(.main-tabview [data-pc-section="header"]) {
  @apply mx-2;
}
:deep(.main-tabview [data-pc-section="headeraction"]) {
  @apply block w-full cursor-pointer border-b-2 border-transparent px-4 py-3 text-center text-sm font-semibold text-theme-text-muted transition-colors duration-200 hover:text-theme-text focus:outline-none;
}
:deep(
  .main-tabview [data-p-highlight="true"] > [data-pc-section="headeraction"]
) {
  @apply border-orange-500 text-orange-500;
}
:deep(.main-tabview [role="tab"][aria-selected="true"] > a) {
  @apply border-orange-500 text-orange-500 !important;
}
:deep(.main-tabview [data-pc-section="inkbar"]) {
  @apply hidden;
}
:deep(.p-tabview-panel) {
  @apply flex flex-grow flex-col;
}
</style>
