<!-- client/components/GitPanel.vue -->
<template>
  <div v-if="gitIntegrationEnabled" class="git-panel p-4 border rounded shadow-lg bg-theme-background-elevated text-theme-text">
    <h2 class="text-xl font-semibold mb-3">Git Integration</h2>

    <div v-if="isLoading" class="text-center">Loading Git info...</div>
    <div v-if="error" class="text-theme-danger p-2 rounded bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700">{{ error }}</div>

    <div v-if="!isLoading && !error">
      <!-- Git Info -->
      <div class="mb-4 p-3 border rounded bg-theme-background">
        <p><strong>Repository:</strong> {{ gitRepoInfo.repo_path_is_git_dir ? 'Valid' : 'Not a Git Repository (or error)' }}</p>
        <p><strong>Current Branch:</strong> {{ gitRepoInfo.current_branch || 'N/A' }}</p>
        <p><strong>Remote:</strong> {{ gitRepoInfo.configured_remote_name }} ({{ gitRepoInfo.configured_remote_url || 'No URL' }})</p>
        <button @click="fetchGitInfo" class="p-button p-button-sm p-button-secondary mt-1">Refresh Info</button>
      </div>

      <!-- Actions -->
      <div class="grid grid-cols-2 md:grid-cols-3 gap-2 mb-4">
        <button @click="performFetchStatus" class="p-button p-button-sm" :disabled="isActionLoading">
          {{ isActionLoading && currentAction === 'status' ? 'Loading...' : 'Status' }}
        </button>
        <button @click="performAddAll" class="p-button p-button-sm p-button-success" :disabled="isActionLoading">
           {{ isActionLoading && currentAction === 'add' ? 'Adding...' : 'Add All' }}
        </button>
        <button @click="performPull" class="p-button p-button-sm p-button-info" :disabled="isActionLoading">
           {{ isActionLoading && currentAction === 'pull' ? 'Pulling...' : 'Pull' }}
        </button>
        <button @click="performPush" class="p-button p-button-sm p-button-info" :disabled="isActionLoading">
           {{ isActionLoading && currentAction === 'push' ? 'Pushing...' : 'Push' }}
        </button>
        <button @click="showCommitModal = true" class="p-button p-button-sm p-button-warning col-span-2 md:col-span-1" :disabled="isActionLoading">Commit</button>
      </div>
      
      <!-- Commit Modal (Simplified) -->
      <div v-if="showCommitModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div class="bg-theme-background p-5 rounded-lg shadow-xl w-full max-w-md">
          <h3 class="text-lg font-medium mb-3">Commit Changes</h3>
          <textarea v-model="commitMessage" placeholder="Enter commit message..." rows="3" class="w-full p-2 border rounded bg-theme-background-elevated focus:ring-theme-brand focus:border-theme-brand"></textarea>
          <div class="mt-3 flex justify-end space-x-2">
            <button @click="showCommitModal = false" class="p-button p-button-sm p-button-secondary">Cancel</button>
            <button @click="performCommit" class="p-button p-button-sm p-button-primary" :disabled="!commitMessage.trim() || isActionLoading">
              {{ isActionLoading && currentAction === 'commit' ? 'Committing...' : 'Commit' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Status/Log Display Area -->
      <div class="mt-4">
        <h3 class="text-lg font-medium mb-2">Status / Output:</h3>
        <div v-if="statusOutput.message" class="p-2 text-sm border rounded mb-2" 
             :class="{
               'bg-green-100 dark:bg-green-900 border-green-300 dark:border-green-700 text-green-700 dark:text-green-300': !statusOutput.stderr,
               'bg-red-100 dark:bg-red-900 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300': statusOutput.stderr
             }">
          <p><strong>{{ statusOutput.message }}</strong></p>
          <pre v-if="statusOutput.stdout" class="whitespace-pre-wrap text-xs mt-1">Stdout: {{ statusOutput.stdout }}</pre>
          <pre v-if="statusOutput.stderr" class="whitespace-pre-wrap text-xs mt-1">Stderr: {{ statusOutput.stderr }}</pre>
        </div>

        <div v-if="gitStatus.files && gitStatus.files.length > 0" class="mb-3">
          <h4 class="font-semibold">Changed Files ({{ gitStatus.files.length }}):</h4>
          <ul class="list-disc pl-5 text-sm max-h-48 overflow-y-auto">
            <li v-for="file in gitStatus.files" :key="file.path" class="font-mono">
              <span class="inline-block w-6 text-center mr-1 rounded" 
                    :class="getFileStatusClass(file.index_status, file.work_tree_status)">
                {{ file.index_status }}{{ file.work_tree_status }}
              </span>
              {{ file.path }}
              <span v-if="file.original_path"> (from {{ file.original_path }})</span>
            </li>
          </ul>
        </div>
        <div v-else-if="gitStatus.files && gitStatus.files.length === 0 && currentAction === 'status_done'" class="text-sm text-theme-text-muted">
          No changes in the working directory.
        </div>
      </div>

      <!-- Git Log (Button to fetch, simplified display) -->
       <div class="mt-4">
        <button @click="fetchGitLog" class="p-button p-button-sm p-button-outlined" :disabled="isActionLoading">
          {{ isActionLoading && currentAction === 'log' ? 'Loading Log...' : 'Show Recent Commits' }}
        </button>
        <div v-if="gitLog.length > 0" class="mt-2 text-sm max-h-60 overflow-y-auto border rounded p-2">
          <h4 class="font-semibold mb-1">Commit Log:</h4>
          <ul>
            <li v-for="entry in gitLog" :key="entry.hash" class="mb-1 pb-1 border-b border-theme-border last:border-b-0">
              <p class="font-mono text-xs text-theme-text-muted">{{ entry.hash.substring(0, 7) }} - {{ entry.date.substring(0,10) }} ({{ entry.author_name }})</p>
              <p>{{ entry.message }}</p>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useGlobalStore } from '../globalStore.js'; // Adjusted path
import { 
  getGitInfo, getGitStatus, gitAddAll, gitCommit, 
  getGitLog as apiGetGitLog, gitPull, gitPush 
} from '../api.js'; // Adjusted path
import { useToast } from "primevue/usetoast"; // For potential future use with apiErrorHandler

const globalStore = useGlobalStore();
const toast = useToast(); // Initialize toast if you plan to use apiErrorHandler or custom toasts

const isLoading = ref(true);
const isActionLoading = ref(false);
const currentAction = ref(''); // To track which action is loading, e.g., 'status', 'commit'
const error = ref(null);
const gitRepoInfo = ref({});
const gitStatus = ref({ files: [] });
const commitMessage = ref('');
const showCommitModal = ref(false);
const statusOutput = ref({}); // For messages from add, commit, pull, push
const gitLog = ref([]);

const gitIntegrationEnabled = computed(() => globalStore.config.value?.flatnotesGitEnabled);

async function fetchGitInfo() {
  if (!gitIntegrationEnabled.value) return;
  isLoading.value = true;
  error.value = null;
  try {
    gitRepoInfo.value = await getGitInfo();
  } catch (err) {
    error.value = `Failed to fetch Git info: ${err.response?.data?.detail || err.message}`;
    // apiErrorHandler(err, toast); // Or use the global handler
  } finally {
    isLoading.value = false;
  }
}

async function performFetchStatus() {
  if (isActionLoading.value) return;
  isActionLoading.value = true;
  currentAction.value = 'status';
  error.value = null;
  statusOutput.value = {};
  try {
    const statusData = await getGitStatus();
    gitStatus.value = statusData;
    statusOutput.value = { message: `Status refreshed. Current branch: ${statusData.current_branch || 'N/A'}` };
  } catch (err) {
    error.value = `Failed to fetch Git status: ${err.response?.data?.detail || err.message}`;
    gitStatus.value = { files: [] }; // Clear status on error
  } finally {
    isActionLoading.value = false;
    currentAction.value = 'status_done';
  }
}

async function performAddAll() {
  if (isActionLoading.value) return;
  isActionLoading.value = true;
  currentAction.value = 'add';
  error.value = null;
  try {
    const response = await gitAddAll();
    statusOutput.value = response;
    await performFetchStatus(); // Refresh status after add
  } catch (err) {
    statusOutput.value = { message: `Error adding files: ${err.response?.data?.detail || err.message}`, stderr: err.response?.data?.stderr || err.message };
  } finally {
    isActionLoading.value = false;
    currentAction.value = '';
  }
}

async function performCommit() {
  if (isActionLoading.value || !commitMessage.value.trim()) return;
  isActionLoading.value = true;
  currentAction.value = 'commit';
  error.value = null;
  try {
    const response = await gitCommit(commitMessage.value);
    statusOutput.value = response;
    commitMessage.value = ''; // Clear message
    showCommitModal.value = false;
    await performFetchStatus(); // Refresh status
    await fetchGitLog(); // Refresh log
  } catch (err) {
    statusOutput.value = { message: `Error committing: ${err.response?.data?.detail || err.message}`, stderr: err.response?.data?.stderr || err.message };
  } finally {
    isActionLoading.value = false;
    currentAction.value = '';
  }
}

async function performGenericGitAction(actionFn, actionName, successMessage) {
  if (isActionLoading.value) return;
  isActionLoading.value = true;
  currentAction.value = actionName;
  error.value = null;
  try {
    const response = await actionFn();
    statusOutput.value = { message: successMessage, stdout: response.stdout, stderr: response.stderr };
    await performFetchStatus(); // Refresh status
    if (actionName === 'pull' || actionName === 'push') { // Also refresh log after pull/push
        await fetchGitLog();
    }
  } catch (err) {
    statusOutput.value = { message: `Error during ${actionName}: ${err.response?.data?.detail || err.message}`, stderr: err.response?.data?.stderr || err.message };
  } finally {
    isActionLoading.value = false;
    currentAction.value = '';
  }
}

function performPull() {
  performGenericGitAction(gitPull, 'pull', 'Pull operation completed.');
}

function performPush() {
  performGenericGitAction(gitPush, 'push', 'Push operation completed.');
}


async function fetchGitLog(limit = 5, page = 1) { // Keep log fetch simple for now
  if (isActionLoading.value && currentAction.value !== 'log' && currentAction.value !== 'commit') return; // Allow log refresh after commit
  const oldAction = currentAction.value;
  const oldIsLoading = isActionLoading.value;

  isActionLoading.value = true;
  currentAction.value = 'log';
  // error.value = null; // Don't clear global error for log fetching unless specific
  try {
    const response = await apiGetGitLog(limit, page);
    gitLog.value = response.log;
  } catch (err) {
    // statusOutput.value = { message: `Error fetching log: ${err.message}`, stderr: err.response?.data?.detail || err.message };
    // For now, log errors to console or a dedicated log error ref
    console.error("Failed to fetch git log:", err);
    gitLog.value = [];
  } finally {
    if (oldAction !== 'log' && oldAction !== 'commit') { // Restore previous loading state if log was a sub-action
        isActionLoading.value = oldIsLoading;
        currentAction.value = oldAction;
    } else {
        isActionLoading.value = false;
        currentAction.value = '';
    }
  }
}

function getFileStatusClass(index, workTree) {
  if (index === 'A' || workTree === 'A') return 'bg-green-500 text-white';
  if (index === 'M' || workTree === 'M') return 'bg-blue-500 text-white';
  if (index === 'D' || workTree === 'D') return 'bg-red-500 text-white';
  if (index === 'R' || workTree === 'R') return 'bg-yellow-500 text-black';
  if (index === 'C' || workTree === 'C') return 'bg-purple-500 text-white';
  if (index === '?' && workTree === '?') return 'bg-gray-400 text-black';
  return 'bg-gray-200 text-black';
}

onMounted(() => {
  if (gitIntegrationEnabled.value) {
    fetchGitInfo();
    performFetchStatus();
    fetchGitLog(); // Fetch initial log
  }
});
</script>

<style scoped>
/* Basic styling for the panel, can be expanded */
/* .git-panel { */
  /* Add specific styles if Tailwind classes are not enough */
/* } */
/* You might want to use PrimeVue button styles or custom styles for buttons */
/* For example, if using PrimeVue Button component, replace <button> with <Button> and adjust props */
/* This example uses Tailwind and basic HTML buttons for simplicity of integration first. */

/* Helper for preformatted text */
.whitespace-pre-wrap {
  white-space: pre-wrap; /* CSS3 */
  white-space: -moz-pre-wrap; /* Mozilla, since 1999 */
  white-space: -pre-wrap; /* Opera 4-6 */
  white-space: -o-pre-wrap; /* Opera 7 */
  word-wrap: break-word; /* Internet Explorer 5.5+ */
}
</style>