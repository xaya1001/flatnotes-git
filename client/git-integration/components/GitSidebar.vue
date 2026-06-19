<!-- client/git-integration/components/GitSidebar.vue -->
<template>
  <div data-right-tool-sidebar class="fixed right-0 top-0 z-40 h-full">
    <!-- Sidebar Component -->
    <Sidebar
      v-model:visible="panelUiStore.isSidebarVisible"
      @show="handleSidebarShow"
      position="right"
      :modal="false"
      :dismissable="false"
      :showCloseIcon="false"
      :pt="{
        mask: { class: 'pointer-events-none' },
        root: {
          'data-right-tool-sidebar': '',
          class:
            'pointer-events-auto h-full border-l border-theme-border bg-theme-background-elevated shadow-none flex flex-col w-full sm:w-96 md:w-[480px]',
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
              title="Refresh all Git data"
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
            class="flex flex-grow items-center justify-center space-x-1 text-xs text-theme-text-muted"
          >
            <template v-if="globalConfig?.flatnotesGitWebhookActive">
              <SvgIcon type="mdi" :path="mdiLanConnect" :size="14" />
              <span>Real-time Fetch Active</span>
            </template>
            <template
              v-else-if="globalConfig?.flatnotesGitAutoFetchInterval > 0"
            >
              <SvgIcon type="mdi" :path="mdiTimerSyncOutline" :size="14" />
              <span>
                Auto-Fetch Active ({{
                  globalConfig.flatnotesGitAutoFetchInterval
                }}
                min)
              </span>
            </template>
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
            <button
              @click="handleClose"
              class="rounded-full p-1 hover:bg-theme-border"
              title="Close Panel"
            >
              <SvgIcon type="mdi" :path="mdiClose" :size="20" />
            </button>
          </div>
        </div>

        <!-- Initial Loading State -->
        <div
          v-if="!statusStore.isInitialLoadComplete && !statusStore.summaryError"
          class="flex flex-grow items-center justify-center"
        >
          <div
            class="flex flex-col items-center space-y-2 text-theme-text-muted"
          >
            <SvgIcon
              type="mdi"
              :path="mdilRefresh"
              :size="32"
              class="animate-spin"
            />
            <span>Loading Git Status...</span>
          </div>
        </div>

        <!-- Welcome / Setup Guide View -->
        <div
          v-else-if="
            statusStore.summaryError &&
            (statusStore.summaryError.includes('not initialized') ||
              statusStore.summaryError.includes('not found'))
          "
          class="flex h-full flex-col p-4 text-sm"
        >
          <div class="mb-4 flex-shrink-0 text-center">
            <SvgIcon
              type="mdi"
              :path="mdiSourceRepository"
              :size="48"
              class="mb-2 text-theme-text-muted"
            />
            <h3 class="text-lg font-semibold">Connect Your Git Repository</h3>
            <p class="mt-1 text-theme-text-muted">
              We couldn't find a Git repository in your notes directory.
            </p>
            <p class="mt-1 text-theme-text-muted">
              Please choose one of the options below.
            </p>
          </div>

          <div class="flex-grow space-y-4 overflow-y-auto pr-2">
            <!-- Option 1: Start a New Repository -->
            <div class="rounded-lg bg-theme-background p-4">
              <h4 class="font-semibold text-theme-text">
                Option 1: Start a New Repository
              </h4>
              <p class="mt-1 text-xs text-theme-text-muted">
                Choose this if you want to create a brand-new repository for
                your existing notes.
              </p>
              <div class="mt-3 rounded bg-black/10 p-3 text-left">
                <p class="font-semibold">Easiest Method:</p>
                <p class="mt-1 text-xs">
                  Set this environment variable and restart Flatnotes:
                </p>
                <code
                  class="font-mono mt-2 block rounded bg-black/20 px-2 py-1 text-xs text-theme-text"
                  >FLATNOTES_GIT_AUTO_INIT=true</code
                >
              </div>
            </div>

            <!-- Option 2: Connect an Existing Remote Repository -->
            <div class="rounded-lg bg-theme-background p-4">
              <h4 class="font-semibold text-theme-text">
                Option 2: Connect an Existing Remote Repo
              </h4>
              <p class="mt-1 text-xs text-theme-text-muted">
                Choose this if you already have a notes repository on GitHub,
                etc. This requires command-line access to your server.
              </p>
              <div class="mt-3 rounded bg-black/10 p-3 text-left">
                <p class="font-semibold">Instructions:</p>
                <div class="mt-2 space-y-3 text-xs">
                  <p>
                    <strong class="text-orange-400">1. IMPORTANT:</strong> Your
                    notes directory on the server
                    <strong class="text-orange-400">must not exist</strong> or
                    be completely empty for `git clone` to work.
                  </p>
                  <p>
                    <strong>2. Clean Up (if needed):</strong> If you have an
                    existing `data` directory (e.g., from a previous setup or
                    accidental `AUTO_INIT`), back up any important files from
                    it, then
                    <strong class="text-orange-400"
                      >remove the entire directory</strong
                    >:
                  </p>
                  <code
                    class="font-mono mt-1 block rounded bg-black/20 px-2 py-1 text-xs text-theme-text"
                    ># From the PARENT directory of 'data': # 1. Back up your
                    notes first! # 2. Then run: rm -rf data</code
                  >
                  <p>
                    <strong>3. Clone the Repository:</strong> In the same parent
                    directory, run `git clone`. This will create a new `data`
                    directory linked to your remote.
                  </p>
                  <p class="mt-1">
                    <strong class="text-orange-400"
                      >You must use the SSH URL</strong
                    >, not HTTPS. You can find it under the "Code" button on
                    your GitHub repository page.
                  </p>
                  <code
                    class="font-mono block rounded bg-black/20 px-2 py-1 text-xs text-theme-text"
                    >git clone git@github.com:YOUR_USERNAME/YOUR_REPO.git
                    data</code
                  >
                  <p>
                    <strong>4.</strong> Ensure file permissions are correct and
                    <strong class="text-orange-400"
                      >your server's SSH key is added to GitHub</strong
                    >. Then, <strong>restart Flatnotes</strong>.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div
            class="mt-4 flex-shrink-0 border-t border-theme-border pt-3 text-center"
          ></div>
        </div>

        <!-- Main View (for initialized repos) -->
        <template v-else>
          <!-- Confirmation Modal -->
          <ConfirmModal
            v-model="panelUiStore.isConfirmModalVisible"
            :title="panelUiStore.confirmModalProps.title"
            :message="panelUiStore.confirmModalProps.message"
            :confirmButtonText="
              panelUiStore.confirmModalProps.confirmButtonText
            "
            :confirmButtonStyle="
              panelUiStore.confirmModalProps.confirmButtonStyle
            "
            @confirm="() => panelUiStore.resolveConfirmation(true)"
            @cancel="() => panelUiStore.resolveConfirmation(false)"
            @reject="() => panelUiStore.resolveConfirmation(false)"
          />

          <!-- Main TabView -->
          <TabView
            class="main-tabview flex min-h-0 flex-grow flex-col"
            :pt="{
              panelContainer: { class: 'flex-grow min-h-0 overflow-hidden' },
              nav: { class: 'main-tabview-nav' },
            }"
          >
            <TabPanel
              :pt="{
                header: {
                  class: isConflictRelated ? 'conflict-tab-header' : '',
                },
                content: { class: 'p-0 flex flex-col h-full' },
              }"
            >
              <template #header>
                <div class="flex items-center space-x-1">
                  <span>Workspace</span>
                  <span
                    v-if="isConflictRelated"
                    class="h-2 w-2 rounded-full bg-red-500"
                  ></span>
                </div>
              </template>

              <!-- AUTHORITATIVE RENDERING DECISION -->
              <ConflictView v-if="isConflictRelated" />
              <WorkspaceTab v-else />
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
        </template>
      </div>
    </Sidebar>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import Sidebar from "primevue/sidebar";
import TabView from "primevue/tabview";
import TabPanel from "primevue/tabpanel";
import SvgIcon from "@jamescoyle/vue-icon";
import { mdilRefresh, mdilPin, mdilPinOff } from "@mdi/light-js";
import {
  mdiClose,
  mdiSourceRepository,
  mdiLanConnect,
  mdiTimerSyncOutline,
} from "@mdi/js";

import { useGlobalStore } from "../../globalStore";
import { usePanelUiStore } from "../stores/panelUiStore";
import { useStatusStore } from "../stores/statusStore";
import { useHistoryStore } from "../stores/historyStore";
import { useLogStore } from "../stores/logStore";
import eventBus from "../services/eventBus";
import { GIT_OPERATION } from "../events";

import ConfirmModal from "../../components/ConfirmModal.vue";
import WorkspaceTab from "./tabs/WorkspaceTab.vue";
import GitLogTab from "./tabs/GitLogTab.vue";
import GitHistoryTab from "./tabs/GitHistoryTab.vue";
import ConflictView from "./ConflictView.vue";

const globalStore = useGlobalStore();
const panelUiStore = usePanelUiStore();
const statusStore = useStatusStore();
const historyStore = useHistoryStore();
const logStore = useLogStore();

const isInitialLoad = ref(true);
const isRefreshing = ref(false);
const globalConfig = computed(() => globalStore.config.value);

const isConflictRelated = computed(() => {
  const state = statusStore.repositoryState;
  if (!state) return false;
  return (
    state.includes("CONFLICT") ||
    state.includes("REBASING") ||
    state.includes("MERGING")
  );
});

function fetchAllSidebarData() {
  return Promise.all([
    statusStore.fetchStatus(),
    historyStore.fetchGitLog(),
    logStore.fetchActivityLog(),
  ]);
}

function handleSidebarShow() {
  if (isInitialLoad.value) {
    return;
  }
  fetchAllSidebarData();
}

function handleClose() {
  panelUiStore.forceHideSidebar();
}

async function refreshAll() {
  isRefreshing.value = true;
  const actionName = "Refresh All Data";
  const operationId = uuidv4();
  eventBus.emit(GIT_OPERATION.WILL_START, {
    actionName,
    operationId,
    persist: false,
  });

  try {
    await fetchAllSidebarData();
    const response = {
      details: { message: "All data refreshed successfully." },
    };
    eventBus.emit(GIT_OPERATION.DID_SUCCEED, {
      actionName,
      operationId,
      response,
    });
  } catch (e) {
    eventBus.emit(GIT_OPERATION.DID_FAIL, {
      actionName,
      operationId,
      err: e,
    });
  } finally {
    isRefreshing.value = false;
  }
}

onMounted(() => {
  if (globalStore.config.value?.flatnotesGitEnabled) {
    statusStore.fetchStatus();
    historyStore.fetchGitLog();
    logStore.initialize();
    isInitialLoad.value = false;
  }
});

onUnmounted(() => {
  if (globalStore.config.value?.flatnotesGitEnabled) {
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

/* --- Main TabView Styling --- */
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

/* Style for the conflicted tab header */
.conflict-tab-header > div > a {
  @apply border-red-500/50 text-red-500;
}
</style>
