// client/git-integration/stores/statusStore.js
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import * as gitApi from "../gitApi";

const POLLING_INTERVAL_MS = 30000;

export const useStatusStore = defineStore("git-status", () => {
  const toast = useToast();
  const router = useRouter();

  // --- STATE ---
  const gitStatus = ref({ files: [] });
  const commitMessage = ref("");
  const isLoading = ref(true);
  const isLoadingSummary = ref(true);
  const summaryError = ref(null);
  const branchName = ref("");
  const filesChangedCount = ref(0);
  const pollingTimer = ref(null);
  const commitsAhead = ref(0);
  const commitsBehind = ref(0);
  const isTrackingUpstream = ref(true);
  const isInitialLoadComplete = ref(false); // Manages initial loading state

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
      commitsAhead.value = data.commits_ahead || 0;
      commitsBehind.value = data.commits_behind || 0;
      isTrackingUpstream.value = data.is_tracking_upstream;
      summaryError.value = null;
    } catch (err) {
      if (err.response?.status === 428) {
        summaryError.value = "Git repository not initialized";
      } else {
        toast.add({
          severity: "error",
          summary: "Error Fetching Detailed Status",
          detail: err.message,
          life: 3000,
        });
      }
      gitStatus.value = { files: [] };
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchStatusSummary() {
    isLoadingSummary.value = true;
    try {
      const summary = await gitApi.getGitStatusSummary();
      branchName.value = summary.current_branch || "N/A";
      filesChangedCount.value = summary.files_changed_count;
      commitsAhead.value = summary.commits_ahead || 0;
      commitsBehind.value = summary.commits_behind || 0;
      isTrackingUpstream.value = summary.is_tracking_upstream;
      summaryError.value = null;
    } catch (err) {
      if (err.response?.status === 428) {
        summaryError.value = "Git repository not initialized";
      } else {
        summaryError.value = err.response?.data?.detail || "Connection failed";
      }
    } finally {
      isLoadingSummary.value = false;
      isInitialLoadComplete.value = true; // Mark initial load as complete
    }
  }

  function startPolling() {
    if (pollingTimer.value) return;
    pollingTimer.value = setInterval(fetchStatusSummary, POLLING_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollingTimer.value) {
      clearInterval(pollingTimer.value);
      pollingTimer.value = null;
    }
  }

  function openNoteInEditor(path) {
    const title = path.replace(/\.md$/, "");
    router.push({ name: "note", params: { title } });
  }

  function clearCommitMessage() {
    commitMessage.value = "";
  }

  return {
    gitStatus,
    commitMessage,
    isLoading,
    isLoadingSummary,
    summaryError,
    branchName,
    filesChangedCount,
    stagedFiles,
    unstagedFiles,
    tooltipText,
    commitsAhead,
    commitsBehind,
    isTrackingUpstream,
    isInitialLoadComplete,
    fetchStatusSummary,
    fetchStatus,
    startPolling,
    stopPolling,
    openNoteInEditor,
    clearCommitMessage,
  };
});
