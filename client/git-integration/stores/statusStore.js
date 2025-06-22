// client/git-integration/stores/statusStore.js
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import * as gitApi from "../gitApi";
import { useConflictStore } from "./conflictStore";
import eventBus from "../eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";

const POLLING_INTERVAL_MS = 30000;

export const useStatusStore = defineStore("git-status", () => {
  const toast = useToast();
  const router = useRouter();
  const conflictStore = useConflictStore();

  // --- STATE ---
  const gitStatus = ref({ files: [] });
  const commitMessage = ref("");
  const isLoading = ref(true);
  const summaryError = ref(null);
  const branchName = ref("");
  const filesChangedCount = ref(0);
  const pollingTimer = ref(null);
  const commitsAhead = ref(0);
  const commitsBehind = ref(0);
  const isTrackingUpstream = ref(true);
  const repositoryState = ref("CLEAN");
  const isInitialLoadComplete = ref(false);

  // --- GETTERS ---
  const stagedFiles = computed(() =>
    gitStatus.value.files.filter(
      (f) => f.index_status !== " " && f.index_status !== "?",
    ),
  );
  const unstagedFiles = computed(() =>
    gitStatus.value.files.filter((f) => f.work_tree_status !== " "),
  );
  const tooltipText = computed(() => {
    if (!isInitialLoadComplete.value) return "Loading Git status...";
    if (summaryError.value) {
      if (summaryError.value.includes("not initialized")) {
        return "Git repository not initialized. Click to see setup instructions.";
      }
      return `Error: ${summaryError.value}.`;
    }
    if (repositoryState.value.startsWith("REBASING")) {
      return "Conflict: Rebase in progress. Click to resolve.";
    }
    if (repositoryState.value.startsWith("MERGING")) {
      return "Conflict: Merge in progress. Click to resolve.";
    }
    let parts = [];
    if (!isTrackingUpstream.value) {
      parts.push("Branch not tracking remote");
    }
    if (commitsBehind.value > 0) parts.push(`${commitsBehind.value} to pull`);
    if (commitsAhead.value > 0) parts.push(`${commitsAhead.value} to push`);
    if (filesChangedCount.value > 0)
      parts.push(`${filesChangedCount.value} changes`);

    if (parts.length === 0) {
      return `Branch '${branchName.value}' is up to date.`;
    }
    return `Branch '${branchName.value}': ${parts.join(", ")}. Click to view.`;
  });

  // --- ACTIONS ---
  async function fetchStatus() {
    isLoading.value = true;
    try {
      const data = await gitApi.getGitStatus();
      gitStatus.value = data;
      branchName.value = data.current_branch || "N/A";
      filesChangedCount.value = data.files_changed_count;
      commitsAhead.value = data.commits_ahead || 0;
      commitsBehind.value = data.commits_behind || 0;
      isTrackingUpstream.value = data.is_tracking_upstream;
      repositoryState.value = data.repository_state;
      summaryError.value = null;

      const state = repositoryState.value;
      if (
        (state.startsWith("REBASING") || state.startsWith("MERGING")) &&
        !conflictStore.isInConflict
      ) {
        const errorData = {
          state: state,
          conflicted_files: data.files
            .filter((f) => f.index_status === "U" || f.work_tree_status === "U")
            .map((f) => f.path),
        };
        conflictStore.enterConflictMode(errorData, { silent: true });
      } else if (
        !state.startsWith("REBASING") &&
        !state.startsWith("MERGING") &&
        conflictStore.isInConflict
      ) {
        conflictStore.exitConflictMode();
      }
    } catch (err) {
      if (err.response?.status === 428) {
        summaryError.value = "Git repository not initialized";
      } else {
        toast.add({
          severity: "error",
          summary: "Error Fetching Detailed Status",
          detail: err.response?.data?.detail || err.message,
          life: 3000,
        });
      }
      gitStatus.value = { files: [] };
    } finally {
      isLoading.value = false;
      isInitialLoadComplete.value = true;
    }
  }

  function startPolling() {
    if (pollingTimer.value) return;
    pollingTimer.value = setInterval(fetchStatus, POLLING_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value);
      pollingTimer.value = null;
    }
  }

  function openNoteInEditor(path) {
    const title = path.replace(/\.md$/, "");
    router.push({
      name: "note",
      params: { title },
      query: { t: Date.now() },
    });
  }

  function clearCommitMessage() {
    commitMessage.value = "";
  }

  // --- Event Listeners ---
  const refreshEvents = [GIT_OPERATION.DID_SUCCEED, GIT_CONFLICT.RESOLVED];
  refreshEvents.forEach((eventName) => {
    eventBus.on(eventName, () => {
      fetchStatus();
    });
  });

  return {
    gitStatus,
    commitMessage,
    isLoading,
    summaryError,
    branchName,
    filesChangedCount,
    stagedFiles,
    unstagedFiles,
    tooltipText,
    commitsAhead,
    commitsBehind,
    isTrackingUpstream,
    repositoryState,
    isInitialLoadComplete,
    fetchStatus,
    startPolling,
    stopPolling,
    openNoteInEditor,
    clearCommitMessage,
  };
});
