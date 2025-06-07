<!-- client/components/GitPanel.vue -->
<template>
  <div
    v-if="gitIntegrationEnabled"
    class="git-panel border rounded-lg shadow-2xl bg-theme-background-elevated text-theme-text max-h-[80vh] flex flex-col"
  >
    <!-- Panel Header -->
    <div class="flex justify-between items-center p-3 border-b border-theme-border flex-shrink-0">
      <h2 class="text-lg font-semibold">Git Sync</h2>
      <button @click="$emit('close')" class="p-1 rounded-full hover:bg-theme-border" title="Close (Esc)">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-5 h-5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>

    <!-- Reusable Confirmation Modal -->
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

    <!-- TabView for Content -->
    <div class="flex-grow overflow-y-auto">
      <div class="git-panel-content">
        <TabView>
          <TabPanel header="Changes">
            <div class="p-2">
              <!-- Commit Area -->
              <div class="mb-4">
                <textarea v-model="commitMessage" placeholder="Commit Message" rows="3" class="w-full p-2 border rounded bg-theme-background focus:ring-theme-brand focus:border-theme-brand text-sm"></textarea>
                <button @click="handleCommit" :disabled="isActionLoading || stagedFiles.length === 0 || !commitMessage.trim()" class="w-full mt-1 p-2 text-sm font-semibold text-white bg-theme-brand rounded hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed">
                  Commit {{ stagedFiles.length }} Staged File(s)
                </button>
              </div>

              <!-- Staged Files -->
              <div v-if="stagedFiles.length > 0">
                <div class="flex justify-between items-center mb-2 ml-1">
                  <h3 class="font-semibold text-sm">Staged Changes ({{ stagedFiles.length }})</h3>
                  <button @click="handleUnstageAll" :disabled="isActionLoading" class="text-xs font-semibold text-theme-text-muted hover:text-theme-text">Unstage All</button>
                </div>
                <DataTable :value="stagedFiles" size="small" :loading="isActionLoading && currentAction === 'status'">
                  <Column header="Status" style="width: 25%"><template #body="slotProps"><span class="p-1 px-2 text-xs rounded-full font-medium" :class="getFileStatusClass(slotProps.data.index_status, '')">{{ getStatusLabel(slotProps.data.index_status) }}</span></template></Column>
                  <Column field="path" header="File"></Column>
                  <Column header="Actions" style="width: 15%" bodyClass="text-center"><template #body="slotProps"><button @click="handleUnstageFile(slotProps.data.path)" :disabled="isActionLoading" class="p-1 text-2xl font-light leading-none text-theme-text-muted hover:text-theme-text" title="Unstage">−</button></template></Column>
                </DataTable>
              </div>

              <!-- Unstaged Files -->
              <div class="mt-4" v-if="unstagedFiles.length > 0">
                <div class="flex justify-between items-center mb-2 ml-1">
                  <h3 class="font-semibold text-sm">Changes ({{ unstagedFiles.length }})</h3>
                  <button @click="handleStageAll" :disabled="isActionLoading" class="text-xs font-semibold text-theme-text-muted hover:text-theme-text">Stage All</button>
                </div>
                <DataTable :value="unstagedFiles" size="small" :loading="isActionLoading && currentAction === 'status'">
                  <Column header="Status" style="width: 25%"><template #body="slotProps"><span class="p-1 px-2 text-xs rounded-full font-medium" :class="getFileStatusClass('', slotProps.data.work_tree_status)">{{ getStatusLabel(slotProps.data.work_tree_status) }}</span></template></Column>
                  <Column field="path" header="File"></Column>
                  <Column header="Actions" style="width: 25%" bodyClass="text-center"><template #body="slotProps"><div class="flex items-center justify-center"><button @click="handleStageFile(slotProps.data.path)" :disabled="isActionLoading" class="p-1 text-2xl font-light leading-none text-theme-text-muted hover:text-theme-text" title="Stage">+</button><button @click="handleDiscardFile(slotProps.data.path)" :disabled="isActionLoading" class="p-1 text-2xl font-light leading-none text-theme-danger ml-2" title="Discard Changes">×</button></div></template></Column>
                </DataTable>
              </div>
              
              <div v-if="stagedFiles.length === 0 && unstagedFiles.length === 0 && !isActionLoading" class="text-center py-4 text-theme-text-muted">No changes detected.</div>
            </div>
          </TabPanel>

          <TabPanel header="History">
              <div class="p-2">
                  <DataTable :value="gitLog" :loading="isActionLoading && currentAction === 'log'" size="small" responsiveLayout="scroll">
                  <Column header="Details">
                      <template #body="slotProps">
                      <div class="font-semibold text-sm">{{ slotProps.data.message }}</div>
                      <div class="text-xs text-theme-text-muted mt-1">
                          <span>{{ slotProps.data.author_name }}</span> committed on <span>{{ new Date(slotProps.data.date).toLocaleDateString() }}</span>
                      </div>
                      </template>
                  </Column>
                  <Column field="hash" header="Hash" style="width: 20%"><template #body="slotProps"><span class="font-mono text-xs">{{ slotProps.data.hash.substring(0, 7) }}</span></template></Column>
                  </DataTable>
                  <div v-if="gitLog.length === 0 && !isActionLoading" class="text-center py-4 text-theme-text-muted">No commit history found.</div>
              </div>
          </TabPanel>

          <TabPanel header="Actions">
            <div class="p-4 grid grid-cols-2 gap-3">
              <button @click="handlePull" :disabled="isActionLoading" class="p-2 text-sm font-semibold rounded bg-theme-background hover:bg-theme-border disabled:opacity-50">Pull</button>
              <button @click="handlePush" :disabled="isActionLoading" class="p-2 text-sm font-semibold rounded bg-theme-background hover:bg-theme-border disabled:opacity-50">Push</button>
              <hr class="col-span-2 my-2 border-theme-border" />
              <h4 class="col-span-2 font-semibold text-sm mb-1 text-theme-danger">Danger Zone</h4>
              <button @click="handleDiscardAll" :disabled="isActionLoading || unstagedFiles.length === 0" class="col-span-2 p-2 text-sm font-semibold rounded border border-theme-danger text-theme-danger hover:bg-red-500/10 disabled:opacity-50 disabled:cursor-not-allowed">Discard All Unstaged Changes...</button>
            </div>
          </TabPanel>
        </TabView>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useGlobalStore } from "../globalStore.js";
import { useToast } from "primevue/usetoast";
import { 
  getGitStatus, getGitLog as apiGetGitLog, gitCommit,
  gitAddAll, gitStageFile, gitUnstageFile, gitDiscardFile, gitDiscardAll, gitPull, gitPush
} from "../api.js";

// PrimeVue Components
import TabView from "primevue/tabview";
import TabPanel from "primevue/tabpanel";
import DataTable from "primevue/datatable";
import Column from "primevue/column";

// Flatnotes Native Components
import ConfirmModal from './ConfirmModal.vue';

const emit = defineEmits(["close"]);
const globalStore = useGlobalStore();
const toast = useToast();

const isActionLoading = ref(false);
const currentAction = ref("");
const gitStatus = ref({ files: [] });
const gitLog = ref([]);
const commitMessage = ref("");
const gitIntegrationEnabled = computed(() => globalStore.config.value?.flatnotesGitEnabled);
const isConfirmModalVisible = ref(false);
const confirmModalProps = ref({});
let confirmModalResolve = null;


function showConfirmation(props) {
  return new Promise((resolve) => {
    confirmModalProps.value = {
      title: props.title,
      message: props.message,
      confirmButtonText: props.confirmButtonText || 'Confirm',
      confirmButtonStyle: props.confirmButtonStyle || 'danger',
    };
    isConfirmModalVisible.value = true;
    confirmModalResolve = (result) => {
        isConfirmModalVisible.value = false;
        resolve(result);
    };
  });
}

const stagedFiles = computed(() => gitStatus.value.files.filter(f => f.index_status !== ' ' && f.index_status !== '?'));
const unstagedFiles = computed(() => gitStatus.value.files.filter(f => f.work_tree_status !== ' '));

function getStatusLabel(statusChar) {
  const map = { A: "Added", M: "Modified", D: "Deleted", R: "Renamed", C: "Copied", "?": "Untracked" };
  return map[statusChar] || statusChar;
}

function getFileStatusClass(index, workTree) {
  const status = index !== " " && index !== "?" ? index : workTree;
  if (status === "A" || status === "C") return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
  if (status === "M") return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
  if (status === "D") return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
  if (status === "R") return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
  if (status === "?") return "bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-300";
  return "bg-gray-200 text-black";
}

async function performFetchStatus() {
  isActionLoading.value = true;
  currentAction.value = 'status';
  gitStatus.value = { files: [] }; 
  try {
    const newStatus = await getGitStatus();
    gitStatus.value = newStatus;
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Error Fetching Status', detail: err.message, life: 3000 });
    gitStatus.value = { files: [] };
  } finally {
    isActionLoading.value = false;
    currentAction.value = '';
  }
}

async function fetchGitLog() {
  isActionLoading.value = true;
  currentAction.value = "log";
  gitLog.value = [];
  try {
    const response = await apiGetGitLog(20, 1);
    gitLog.value = response.log;
  } catch (err) {
    toast.add({ severity: 'error', summary: 'Error Fetching Log', detail: err.message, life: 3000 });
    gitLog.value = [];
  } finally {
    isActionLoading.value = false;
    currentAction.value = '';
  }
}

async function handleFileOperation(operationFunc, filepath, actionName) {
  isActionLoading.value = true;
  currentAction.value = actionName;
  try {
    const response = await operationFunc(filepath);
    toast.add({ severity: 'success', summary: 'Success', detail: response.message, life: 3000 });
    await performFetchStatus();
  } catch (err) {
    toast.add({ severity: 'error', summary: `Error ${actionName}`, detail: err.response?.data?.detail || err.message, life: 5000 });
  } finally {
    isActionLoading.value = false;
    currentAction.value = '';
  }
}

function handleStageFile(filepath) { handleFileOperation(gitStageFile, filepath, 'Staging'); }
function handleUnstageFile(filepath) { handleFileOperation(gitUnstageFile, filepath, 'Unstaging'); }

async function handleDiscardFile(filepath) {
  const confirmed = await showConfirmation({
    title: 'Confirm Discard',
    message: `Are you sure you want to discard changes to '${filepath}'? This cannot be undone.`,
    confirmButtonStyle: 'danger',
    confirmButtonText: 'Discard'
  });
  if (confirmed) {
    handleFileOperation(gitDiscardFile, filepath, 'Discarding');
  }
}

async function handleStageAll() {
    isActionLoading.value = true;
    currentAction.value = 'Staging All';
    try {
        await gitAddAll();
        toast.add({ severity: 'success', summary: 'Success', detail: 'All changes staged.', life: 3000 });
        await performFetchStatus();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error Staging All', detail: err.response?.data?.detail || err.message, life: 5000 });
    } finally {
        isActionLoading.value = false;
        currentAction.value = '';
    }
}

async function handleUnstageAll() {
    isActionLoading.value = true;
    currentAction.value = 'Unstaging All';
    const filesToUnstage = [...stagedFiles.value];
    if (filesToUnstage.length === 0) {
        isActionLoading.value = false;
        currentAction.value = '';
        return;
    }
    try {
        for (const file of filesToUnstage) {
            await gitUnstageFile(file.path);
        }
        toast.add({ severity: 'success', summary: 'Success', detail: 'All staged files have been unstaged.', life: 3000 });
        await performFetchStatus();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Error Unstaging All', detail: err.response?.data?.detail || err.message, life: 5000 });
        await performFetchStatus();
    } finally {
        isActionLoading.value = false;
        currentAction.value = '';
    }
}

async function handleCommit() {
    isActionLoading.value = true;
    currentAction.value = 'Committing';
    try {
        const response = await gitCommit(commitMessage.value);
        toast.add({ severity: 'success', summary: 'Committed', detail: response.message, life: 3000 });
        commitMessage.value = '';
        await performFetchStatus();
        await fetchGitLog();
    } catch (err) {
        toast.add({ severity: 'error', summary: 'Commit Error', detail: err.response?.data?.detail || err.message, life: 5000 });
    } finally {
        isActionLoading.value = false;
        currentAction.value = '';
    }
}

async function handleDiscardAll() {
  const confirmed = await showConfirmation({
    title: 'Confirm Discard All',
    message: 'Are you sure you want to discard ALL unstaged changes? This will delete new untracked files and cannot be undone.',
    confirmButtonStyle: 'danger',
    confirmButtonText: 'Discard All'
  });

  if (confirmed) {
    isActionLoading.value = true;
    currentAction.value = 'Discarding All';
    try {
      const response = await gitDiscardAll();
      toast.add({ severity: 'success', summary: 'Success', detail: response.message, life: 3000 });
      await performFetchStatus();
    } catch (err) {
      toast.add({ severity: 'error', summary: 'Error Discarding All', detail: err.response?.data?.detail || err.message, life: 5000 });
    } finally {
      isActionLoading.value = false;
      currentAction.value = '';
    }
  }
}

async function handleGenericAction(actionFunc, actionName) {
    isActionLoading.value = true;
    currentAction.value = actionName;
    try {
        const response = await actionFunc();
        toast.add({ 
            severity: response.stderr ? 'warn' : 'info', 
            summary: actionName, 
            detail: response.stdout || response.stderr || response.message, 
            life: 5000 
        });
        await performFetchStatus();
        await fetchGitLog();
    } catch (err) {
        toast.add({ severity: 'error', summary: `${actionName} Error`, detail: err.response?.data?.stderr || err.response?.data?.detail || err.message, life: 5000 });
    } finally {
        isActionLoading.value = false;
        currentAction.value = '';
    }
}

function handlePull() { handleGenericAction(gitPull, 'Pull'); }
function handlePush() { handleGenericAction(gitPush, 'Push'); }

onMounted(() => {
  if (gitIntegrationEnabled.value) {
    performFetchStatus();
    fetchGitLog();
  }
});

</script>

<style scoped>
.git-panel-content {
  height: 30rem;
  display: flex;
  flex-direction: column;
}

:deep(.p-tabview) {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

:deep(.p-tabview-panels) {
  flex-grow: 1;
  overflow-y: auto;
}

:deep([data-pc-section="nav"]) {
  @apply flex border-b border-theme-border px-2;
}

:deep([data-pc-section="header"]) {
  @apply mr-2;
}

:deep([data-pc-section="headeraction"]) {
  @apply block py-3 px-2 text-sm font-semibold transition-colors duration-200
         border-b-2 border-transparent text-theme-text-muted hover:text-theme-text focus:outline-none
         cursor-pointer;
}

:deep([data-p-highlight="true"] > [data-pc-section="headeraction"]) {
  @apply border-theme-brand text-theme-brand;
}

:deep([data-pc-section="inkbar"]) {
  @apply hidden;
}

:deep([data-pc-section="panelcontainer"]) {
  @apply p-0;
}

:deep(.p-datatable-wrapper) {
  @apply overflow-x-hidden;
}

:deep(.p-datatable .p-datatable-thead > tr > th) {
  @apply bg-theme-background-elevated text-theme-text-muted border-b border-theme-border 
         text-xs uppercase font-semibold px-2 py-3;
}

:deep(.p-datatable .p-datatable-tbody > tr) {
  @apply bg-transparent text-theme-text;
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  @apply border-0 border-b border-theme-border py-2 px-2 text-sm;
}
</style>