<template>
  <div
    v-if="gitIntegrationEnabled"
    class="git-panel flex flex-col rounded-lg border bg-theme-background-elevated text-theme-text shadow-2xl"
  >
    <!-- Panel Header (无变化) -->
    <div
      class="flex flex-shrink-0 items-center justify-between border-b border-theme-border p-3"
    >
      <div class="flex items-center space-x-2">
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
      <div class="flex items-center space-x-1">
        <button
          @click="togglePin"
          class="rounded-full p-1 hover:bg-theme-border"
          :title="isPinned ? 'Unpin Panel' : 'Pin Panel'"
        >
          <SvgIcon
            type="mdi"
            :path="isPinned ? mdilPin : mdilPinOff"
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

    <ConfirmModal
      v-model="isConfirmModalVisible"
      :title="confirmModalProps.title"
      :message="confirmModalProps.message"
      :confirmButtonText="confirmModalProps.confirmButtonText"
      :confirmButtonStyle="confirmModalProps.confirmButtonStyle"
      @confirm="() => confirmModalResolve(true)"
      @cancel="() => confirmModalResolve(false)"
      @reject="() => confirmModalResolve(false)"
    />

    <!-- 
      TabView for Content:
      我们将在这里应用正确的 Pass Through (PT) 属性来最终修复布局。
    -->
    <TabView
      class="flex min-h-0 flex-grow flex-col"
      :pt="{
        /* 
          关键修复 1: 确保 panelContainer (包裹所有标签页的容器) 
          拥有 flex-grow 来填充空间，并且最重要的是有 overflow-hidden 来创建高度边界。
        */
        panelContainer: { class: 'flex-grow min-h-0 overflow-hidden' }
      }"
    >
      <!-- 
        关键修复 2: 简化每个 TabPanel 的内部结构。
        我们通过 pt.content 将 flex 布局和内边距直接应用到 TabPanel 的内容根元素上，
        并移除模板中多余的 div 包装器。
      -->
      <TabPanel
        header="Changes"
        :pt="{ content: { class: 'p-2 flex flex-col h-full' } }"
      >
        <!-- Commit & Sync Area (Fixed Size) -->
        <div class="mb-4 flex-shrink-0">
          <textarea
            v-model="commitMessage"
            placeholder="Commit Message"
            rows="3"
            class="w-full rounded border bg-theme-background p-2 text-sm focus:border-theme-brand focus:ring-theme-brand"
          ></textarea>
          <div class="mt-1 flex space-x-2">
            <button
              @click="handleCommit"
              :disabled="
                isActionLoading ||
                stagedFiles.length === 0 ||
                !commitMessage.trim()
              "
              class="w-1/2 rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:cursor-not-allowed disabled:opacity-50"
            >
              Commit Staged
            </button>
            <button
              @click="handleSync"
              :disabled="
                isActionLoading ||
                (stagedFiles.length === 0 && unstagedFiles.length === 0)
              "
              class="w-1/2 rounded bg-theme-brand p-2 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Commit & Sync
            </button>
          </div>
        </div>

        <!-- Scrollable content area -->
        <div class="min-h-0 flex-grow overflow-y-auto">
          <!-- Staged Files -->
          <div class="mb-4">
            <div class="mb-2 ml-1 flex items-center justify-between">
              <h3 class="text-sm font-semibold">
                Staged Changes ({{ stagedFiles.length }})
              </h3>
              <button
                @click="handleUnstageAll"
                :disabled="isActionLoading || stagedFiles.length === 0"
                class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:opacity-50"
              >
                Unstage All
              </button>
            </div>
            <div v-if="stagedFiles.length > 0">
              <DataTable
                :value="stagedFiles"
                size="small"
                :loading="isActionLoading && currentAction === 'status'"
                :tableStyle="{ 'table-layout': 'fixed', width: '100%' }"
              >
                <Column
                  field="path"
                  header="File"
                  style="width: 60%"
                  bodyStyle="word-break: break-all;"
                ></Column>
                <Column header="Status" style="width: 20%"
                  ><template #body="slotProps"
                    ><span
                      class="rounded-full p-1 px-2 text-xs font-medium"
                      :class="
                        getFileStatusClass(slotProps.data.index_status, '')
                      "
                      >{{ getStatusLabel(slotProps.data.index_status) }}</span
                    ></template
                  ></Column
                >
                <Column
                  header="Actions"
                  style="width: 20%"
                  bodyClass="text-center"
                  ><template #body="slotProps"
                    ><div class="flex items-center justify-center space-x-2">
                      <button
                        v-if="slotProps.data.path.endsWith('.md')"
                        @click="openNoteInEditor(slotProps.data.path)"
                        class="p-1 text-theme-text-muted hover:text-theme-text"
                        title="Open File"
                      >
                        <SvgIcon
                          type="mdi"
                          :path="mdilFile"
                          :size="16"
                        /></button
                      ><button
                        @click="handleUnstageFile(slotProps.data.path)"
                        :disabled="isActionLoading"
                        class="p-1 text-2xl font-light leading-none text-theme-text-muted hover:text-theme-text"
                        title="Unstage"
                      >
                        −
                      </button>
                    </div></template
                  ></Column
                >
              </DataTable>
            </div>
            <p v-else class="py-4 text-center text-sm text-theme-text-muted">
              No staged changes.
            </p>
          </div>

          <!-- Unstaged Files -->
          <div>
            <div class="mb-2 ml-1 flex items-center justify-between">
              <h3 class="text-sm font-semibold">
                Changes ({{ unstagedFiles.length }})
              </h3>
              <button
                @click="handleStageAll"
                :disabled="isActionLoading || unstagedFiles.length === 0"
                class="text-xs font-semibold text-theme-text-muted hover:text-theme-text disabled:opacity-50"
              >
                Stage All
              </button>
            </div>
            <div v-if="unstagedFiles.length > 0">
              <DataTable
                :value="unstagedFiles"
                size="small"
                :loading="isActionLoading && currentAction === 'status'"
                :tableStyle="{ 'table-layout': 'fixed', width: '100%' }"
              >
                <Column
                  field="path"
                  header="File"
                  style="width: 60%"
                  bodyStyle="word-break: break-all;"
                ></Column>
                <Column header="Status" style="width: 20%"
                  ><template #body="slotProps"
                    ><span
                      class="rounded-full p-1 px-2 text-xs font-medium"
                      :class="
                        getFileStatusClass('', slotProps.data.work_tree_status)
                      "
                      >{{
                        getStatusLabel(slotProps.data.work_tree_status)
                      }}</span
                    ></template
                  ></Column
                >
                <Column
                  header="Actions"
                  style="width: 20%"
                  bodyClass="text-center"
                  ><template #body="slotProps"
                    ><div class="flex items-center justify-center space-x-2">
                      <button
                        v-if="slotProps.data.path.endsWith('.md')"
                        @click="openNoteInEditor(slotProps.data.path)"
                        class="p-1 text-theme-text-muted hover:text-theme-text"
                        title="Open File"
                      >
                        <SvgIcon
                          type="mdi"
                          :path="mdilFile"
                          :size="16"
                        /></button
                      ><button
                        @click="handleStageFile(slotProps.data.path)"
                        :disabled="isActionLoading"
                        class="p-1 text-2xl font-light leading-none text-theme-text-muted hover:text-theme-text"
                        title="Stage"
                      >
                        +</button
                      ><button
                        @click="handleDiscardFile(slotProps.data.path)"
                        :disabled="isActionLoading"
                        class="p-1"
                        title="Discard Changes"
                      >
                        <SvgIcon
                          type="mdi"
                          :path="mdiClose"
                          :size="16"
                          class="text-theme-danger"
                        />
                      </button></div></template
                ></Column>
              </DataTable>
            </div>
            <p v-else class="py-4 text-center text-sm text-theme-text-muted">
              No unstaged changes.
            </p>
          </div>
        </div>
      </TabPanel>

      <TabPanel
        header="History"
        :pt="{ content: { class: 'p-2 flex flex-col h-full' } }"
      >
        <div class="min-h-0 flex-grow overflow-y-auto">
          <DataTable
            :value="gitLog"
            :loading="isActionLoading && currentAction === 'log'"
            size="small"
            :tableStyle="{ 'table-layout': 'fixed', width: '100%' }"
            responsiveLayout="scroll"
          >
            <Column header="Details">
              <template #body="slotProps">
                <div class="break-words text-sm font-semibold">
                  {{ slotProps.data.message }}
                </div>
                <div class="mt-1 text-xs text-theme-text-muted">
                  <span>{{ slotProps.data.author_name }}</span> committed on
                  <span>{{
                    new Date(slotProps.data.date).toLocaleDateString()
                  }}</span>
                </div>
              </template>
            </Column>
            <Column field="hash" header="Hash" style="width: 20%"
              ><template #body="slotProps"
                ><span class="font-mono text-xs">{{
                  slotProps.data.hash.substring(0, 7)
                }}</span></template
              ></Column
            >
          </DataTable>
          <div
            v-if="gitLog.length === 0 && !isActionLoading"
            class="py-4 text-center text-theme-text-muted"
          >
            No commit history found.
          </div>
        </div>
      </TabPanel>

      <TabPanel
        header="Actions"
        :pt="{ content: { class: 'p-4 flex flex-col h-full' } }"
      >
        <div class="min-h-0 flex-grow overflow-y-auto">
          <div class="grid grid-cols-2 gap-3">
            <button
              @click="handlePull"
              :disabled="isActionLoading"
              class="rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:opacity-50"
            >
              Pull
            </button>
            <button
              @click="handlePush"
              :disabled="isActionLoading"
              class="rounded bg-theme-background p-2 text-sm font-semibold hover:bg-theme-border disabled:opacity-50"
            >
              Push
            </button>
          </div>
          <hr class="my-4 border-theme-border" />
          <div>
            <h4 class="mb-2 text-sm font-semibold">Automation Status</h4>
            <div
              class="rounded-md bg-theme-background p-3 text-sm text-theme-text-muted"
            >
              <div class="flex items-center justify-between">
                <span>Automatic Sync</span>
                <Toggle
                  v-if="
                    globalStore.config.value.flatnotesGitAutoSyncInterval > 0
                  "
                  :isOn="!isAutoSyncPaused"
                  :label="isAutoSyncPaused ? 'Paused' : 'Enabled'"
                  @click="toggleAutoSyncPause"
                  :disabled="isActionLoading"
                />
                <span
                  v-else
                  class="rounded-full bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                  >Disabled</span
                >
              </div>
              <div
                v-if="globalStore.config.value.flatnotesGitAutoSyncInterval > 0"
                class="mt-2 text-xs"
              >
                Syncs automatically every
                <strong>{{
                  globalStore.config.value.flatnotesGitAutoSyncInterval
                }}</strong>
                minutes.
                <span
                  v-if="isAutoSyncPaused"
                  class="font-semibold text-yellow-600 dark:text-yellow-400"
                  >(Currently Paused)</span
                >
              </div>
              <div v-else class="mt-2 text-xs">
                Set
                <code class="text-xs">FLATNOTES_GIT_AUTO_SYNC_INTERVAL</code> to
                enable.
              </div>
            </div>
          </div>
          <hr class="my-4 border-theme-border" />
          <div>
            <h4 class="mb-1 text-sm font-semibold text-theme-danger">
              Danger Zone
            </h4>
            <button
              @click="handleDiscardAll"
              :disabled="isActionLoading || unstagedFiles.length === 0"
              class="w-full rounded border border-theme-danger p-2 text-sm font-semibold text-theme-danger hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Discard All Unstaged Changes...
            </button>
          </div>
        </div>
      </TabPanel>

      <TabPanel
        header="Log"
        :pt="{ content: { class: 'p-2 flex flex-col h-full' } }"
      >
        <!-- Fixed size filter area -->
        <div class="mb-2 flex flex-shrink-0 items-center space-x-2">
          <button
            v-for="filter in logLevelOptions"
            :key="filter.value"
            @click="setLogLevelFilter(filter.value)"
            class="rounded-full px-3 py-1 text-xs font-semibold transition-colors duration-200"
            :class="[
              activeLogLevelFilter === filter.value
                ? 'text-white'
                : getLogLevelTextColorClass(filter.value),
              activeLogLevelFilter === filter.value
                ? getLogLevelBgClass(filter.value)
                : 'bg-theme-background hover:bg-theme-border'
            ]"
          >
            {{ filter.name }}
          </button>
        </div>
        <!-- Scrollable content area -->
        <div class="min-h-0 flex-grow overflow-y-auto">
          <div v-if="filteredLogs.length > 0">
            <div
              v-for="log in filteredLogs"
              :key="log.id"
              class="border-b border-theme-border p-2 last:border-b-0"
            >
              <div class="flex items-center">
                <span
                  class="mr-2 h-3 w-3 flex-shrink-0 rounded-full"
                  :class="getLogLevelBgClass(log.level)"
                ></span>
                <span class="mr-2 text-sm font-semibold">{{
                  log.message
                }}</span>
                <span class="ml-auto text-xs text-theme-text-muted">{{
                  new Date(log.timestamp).toLocaleTimeString()
                }}</span>
              </div>
              <pre
                v-if="log.details"
                class="mt-1 max-h-48 overflow-auto whitespace-pre-wrap rounded-md bg-theme-background p-2 text-xs"
                >{{ log.details }}</pre
              >
            </div>
          </div>
          <p v-else class="py-4 text-center text-sm text-theme-text-muted">
            No logs to display for this level.
          </p>
        </div>
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup>
// Script部分无需任何修改
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useGlobalStore } from '../globalStore.js';
import { useLogStore } from '../logStore.js';
import { useToast } from 'primevue/usetoast';
import { useRouter } from 'vue-router';
import {
  getGitStatus,
  getGitLog as apiGetGitLog,
  gitCommit,
  gitSyncWorkspace,
  gitStageFile,
  gitUnstageFile,
  gitUnstageAll,
  gitDiscardFile,
  gitDiscardAll,
  gitPull,
  gitPush,
  getAutoSyncState,
  pauseAutoSync,
  resumeAutoSync,
  getGitActivityLog,
  gitAddAll
} from '../api.js';

// --- Icons ---
import SvgIcon from '@jamescoyle/vue-icon';
import { mdilRefresh, mdilFile, mdilPin, mdilPinOff } from '@mdi/light-js';
import { mdiClose } from '@mdi/js';

// --- Components ---
import Toggle from './Toggle.vue';
import ConfirmModal from './ConfirmModal.vue';
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';

// --- State & Refs ---
const emit = defineEmits(['close', 'pin-toggled']);
const globalStore = useGlobalStore();
const logStore = useLogStore();
const toast = useToast();
const router = useRouter();

const isActionLoading = ref(false);
const isRefreshing = ref(false);
const currentAction = ref('');
const gitStatus = ref({ files: [] });
const gitLog = ref([]);
const commitMessage = ref('');
const isPinned = ref(false);
const isConfirmModalVisible = ref(false);
const confirmModalProps = ref({});
let confirmModalResolve = null;
const isAutoSyncPaused = ref(false);
let logPollInterval = null;

const gitIntegrationEnabled = computed(
  () => globalStore.config.value?.flatnotesGitEnabled
);
const stagedFiles = computed(() =>
  gitStatus.value.files.filter(
    (f) => f.index_status !== ' ' && f.index_status !== '?'
  )
);
const unstagedFiles = computed(() =>
  gitStatus.value.files.filter((f) => f.work_tree_status !== ' ')
);

// --- Log Filtering Logic ---
const activeLogLevelFilter = ref('all');
const logLevelOptions = ref([
  { name: 'All', value: 'all' },
  { name: 'Success', value: 'success' },
  { name: 'Error', value: 'error' },
  { name: 'Info', value: 'info' },
  { name: 'Warn', value: 'warn' }
]);
const filteredLogs = computed(() => {
  if (activeLogLevelFilter.value === 'all') {
    return logStore.logs;
  }
  return logStore.logs.filter(
    (log) => log.level === activeLogLevelFilter.value
  );
});

function setLogLevelFilter(level) {
  activeLogLevelFilter.value = level;
}

// --- UI Interaction & Style Logic ---
function togglePin() {
  isPinned.value = !isPinned.value;
  emit('pin-toggled', isPinned.value);
}

function openNoteInEditor(path) {
  const title = path.replace(/\.md$/, '');
  router.push({ name: 'note', params: { title } });
  emit('close');
}

function showConfirmation(props) {
  return new Promise((resolve) => {
    confirmModalProps.value = {
      title: props.title,
      message: props.message,
      confirmButtonText: props.confirmButtonText || 'Confirm',
      confirmButtonStyle: props.confirmButtonStyle || 'danger'
    };
    isConfirmModalVisible.value = true;
    confirmModalResolve = (result) => {
      isConfirmModalVisible.value = false;
      if (!result) {
        logStore.addLog({
          level: 'info',
          message: `${props.title}: Operation cancelled by user.`
        });
      }
      resolve(result);
    };
  });
}

function getStatusLabel(statusChar) {
  const map = {
    A: 'Added',
    M: 'Modified',
    D: 'Deleted',
    R: 'Renamed',
    C: 'Copied',
    '?': 'Untracked'
  };
  return map[statusChar] || statusChar;
}

function getFileStatusClass(index, workTree) {
  const status = index !== ' ' && index !== '?' ? index : workTree;
  if (status === 'A' || status === 'C')
    return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
  if (status === 'M')
    return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
  if (status === 'D')
    return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
  if (status === 'R')
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
  if (status === '?')
    return 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  return 'bg-gray-200 text-black';
}

function getLogLevelBgClass(level) {
  const map = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    warn: 'bg-yellow-500',
    info: 'bg-blue-500',
    all: 'bg-gray-500'
  };
  return map[level] || 'bg-gray-400';
}

function getLogLevelTextColorClass(level) {
  const map = {
    success: 'text-green-600 dark:text-green-400',
    error: 'text-red-600 dark:text-red-400',
    warn: 'text-yellow-600 dark:text-yellow-400',
    info: 'text-blue-600 dark:text-blue-400',
    all: 'text-gray-600 dark:text-gray-400'
  };
  return map[level] || 'text-gray-400';
}

// --- Data Fetching & Refresh Logic ---
async function performFetchStatus() {
  currentAction.value = 'status';
  gitStatus.value = { files: [] };
  try {
    const newStatus = await getGitStatus();
    gitStatus.value = newStatus;
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error Fetching Status',
      detail: err.message,
      life: 3000
    });
    gitStatus.value = { files: [] };
  } finally {
    currentAction.value = '';
  }
}

async function fetchGitLog() {
  currentAction.value = 'log';
  gitLog.value = [];
  try {
    const response = await apiGetGitLog(20, 1);
    gitLog.value = response.log;
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Error Fetching Log',
      detail: err.message,
      life: 3000
    });
    gitLog.value = [];
  } finally {
    currentAction.value = '';
  }
}

async function fetchActivityLog() {
  try {
    const backendLogs = await getGitActivityLog();
    logStore.mergeBackendLogs(backendLogs);
  } catch (error) {
    console.error('Failed to fetch activity log from backend:', error);
  }
}

async function refreshAll() {
  isRefreshing.value = true;
  const pendingLogId = logStore.addPendingLog('Refreshing all data...');
  await Promise.all([performFetchStatus(), fetchGitLog(), fetchActivityLog()]);
  logStore.updateLog(pendingLogId, {
    level: 'success',
    message: 'All data refreshed.',
    details: null
  });
  isRefreshing.value = false;
}

// --- Git Action Handlers ---
async function performGitAction(actionFunc, args, actionName, successMessage) {
  isActionLoading.value = true;
  const pendingLogId = logStore.addPendingLog(`${actionName}...`);
  try {
    const response = await actionFunc(...args);
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: successMessage,
      life: 3000
    });
    logStore.updateLog(pendingLogId, {
      level: 'success',
      message: successMessage,
      details: response.stdout || response.message || null
    });
    await performFetchStatus();
    if (
      actionName.includes('Commit') ||
      actionName.includes('Sync') ||
      actionName.includes('Pull')
    ) {
      await fetchGitLog();
    }
  } catch (err) {
    const errorMessage = err.response?.data?.detail || err.message;
    toast.add({
      severity: 'error',
      summary: `Error: ${actionName}`,
      detail: errorMessage,
      life: 5000
    });
    logStore.updateLog(pendingLogId, {
      level: 'error',
      message: `Failed: ${actionName}`,
      details: errorMessage
    });
  } finally {
    isActionLoading.value = false;
  }
}

function handleStageFile(filepath) {
  performGitAction(
    gitStageFile,
    [filepath],
    'Stage File',
    `File '${filepath}' staged.`
  );
}
function handleStageAll() {
  performGitAction(gitAddAll, [], 'Stage All', 'All changes staged.');
}
function handleUnstageFile(filepath) {
  performGitAction(
    gitUnstageFile,
    [filepath],
    'Unstage File',
    `File '${filepath}' unstaged.`
  );
}
function handleUnstageAll() {
  performGitAction(
    gitUnstageAll,
    [],
    'Unstage All',
    'All staged changes unstaged.'
  );
}

async function handleDiscardFile(filepath) {
  const confirmed = await showConfirmation({
    title: 'Confirm Discard',
    message: `Discard changes to '${filepath}'? This cannot be undone.`,
    confirmButtonText: 'Discard'
  });
  if (confirmed) {
    performGitAction(
      gitDiscardFile,
      [filepath],
      'Discard File',
      `Changes to '${filepath}' discarded.`
    );
  }
}

async function handleDiscardAll() {
  const confirmed = await showConfirmation({
    title: 'Confirm Discard All',
    message: `Discard ALL unstaged changes? This will delete new files and cannot be undone.`,
    confirmButtonText: 'Discard All'
  });
  if (confirmed) {
    performGitAction(
      gitDiscardAll,
      [],
      'Discard All',
      'All unstaged changes discarded.'
    );
  }
}

function handleCommit() {
  performGitAction(
    gitCommit,
    [commitMessage.value],
    'Commit',
    'Changes committed.'
  );
  commitMessage.value = '';
}
function handleSync() {
  performGitAction(
    gitSyncWorkspace,
    [commitMessage.value],
    'Commit & Sync',
    'Workspace synced.'
  );
  commitMessage.value = '';
}
function handlePull() {
  performGitAction(gitPull, [], 'Pull', 'Pull operation completed.');
}
function handlePush() {
  performGitAction(gitPush, [], 'Push', 'Push operation completed.');
}

async function toggleAutoSyncPause() {
  const action = isAutoSyncPaused.value ? resumeAutoSync : pauseAutoSync;
  const actionName = isAutoSyncPaused.value
    ? 'Resume Auto-Sync'
    : 'Pause Auto-Sync';
  const successMessage = `Auto-sync ${isAutoSyncPaused.value ? 'resumed' : 'paused'}.`;

  isActionLoading.value = true;
  const pendingLogId = logStore.addPendingLog(`${actionName}...`);
  try {
    const response = await action();
    isAutoSyncPaused.value = response.paused;
    toast.add({
      severity: 'info',
      summary: 'Auto-Sync',
      detail: successMessage,
      life: 3000
    });
    logStore.updateLog(pendingLogId, {
      level: 'success',
      message: successMessage,
      details: null
    });
  } catch (err) {
    const errorMessage =
      err.response?.data?.detail || 'Failed to update auto-sync state.';
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: errorMessage,
      life: 3000
    });
    logStore.updateLog(pendingLogId, {
      level: 'error',
      message: `Failed: ${actionName}`,
      details: errorMessage
    });
  } finally {
    isActionLoading.value = false;
  }
}

// --- Lifecycle Hooks ---
onMounted(async () => {
  if (gitIntegrationEnabled.value) {
    refreshAll();
    logPollInterval = setInterval(fetchActivityLog, 10000);

    if (globalStore.config.value.flatnotesGitAutoSyncInterval > 0) {
      try {
        const state = await getAutoSyncState();
        isAutoSyncPaused.value = state.paused;
      } catch (error) {
        console.error('Failed to get initial auto-sync state', error);
      }
    }
  }
});

onUnmounted(() => {
  if (logPollInterval) {
    clearInterval(logPollInterval);
  }
});
</script>

<style scoped>
.git-panel {
  height: 85vh;
}

/* Script部分无需任何修改 */

/* Tab Navigation Theming */
:deep([data-pc-section='nav']) {
  @apply flex flex-shrink-0 border-b border-theme-border px-2;
}
:deep([data-pc-section='header']) {
  @apply mr-2;
}
:deep([data-pc-section='headeraction']) {
  @apply block cursor-pointer border-b-2 border-transparent px-2 py-3 text-sm font-semibold text-theme-text-muted transition-colors duration-200 hover:text-theme-text focus:outline-none;
}
:deep([data-p-highlight='true'] > [data-pc-section='headeraction']) {
  @apply border-theme-brand text-theme-brand;
}
:deep([data-pc-section='inkbar']) {
  @apply hidden;
}

/* DataTable Theming */
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
