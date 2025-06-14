// client/git-integration/stores/statusStore.js
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import * as gitApi from "../gitApi";
import { connectToGitEvents } from "../eventSource";

/**
 * Manages the state related to `git status`, including staged/unstaged files,
 * the commit message, and the summary for the status indicator.
 */
export const useStatusStore = defineStore("git-status", () => {
  // -- DEPS --
  const toast = useToast();
  const router = useRouter();

  // -- STATE --
  const gitStatus = ref({ files: [] });
  const commitMessage = ref("");
  const isLoading = ref(true); // For detailed status

  // For GitStatusIndicator
  const isLoadingSummary = ref(true);
  const summaryError = ref(null);
  const branchName = ref("");
  const filesChangedCount = ref(0);

  // -- GETTERS --
  const stagedFiles = computed(() =>
    gitStatus.value.files.filter(
      (f) => f.index_status !== " " && f.index_status !== "?",
    ),
  );

  const unstagedFiles = computed(() =>
    gitStatus.value.files.filter((f) => f.work_tree_status !== " "),
  );

  const tooltipText = computed(() => {
    if (isLoadingSummary.value) return "Loading Git status...";
    if (summaryError.value)
      return `Error: ${summaryError.value}. Refresh to reconnect.`;
    if (filesChangedCount.value > 0)
      return `${filesChangedCount.value} changes detected on branch '${branchName.value}'. Click to view.`;
    return `On branch '${branchName.value}'. Synced.`;
  });

  // -- ACTIONS --
  async function fetchStatus() {
    isLoading.value = true;
    try {
      gitStatus.value = await gitApi.getGitStatus();
    } catch (err) {
      toast.add({
        severity: "error",
        summary: "Error Fetching Status",
        detail: err.message,
        life: 3000,
      });
      gitStatus.value = { files: [] }; // Reset on error
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchStatusSummary() {
    try {
      const summary = await gitApi.getGitStatusSummary();
      branchName.value = summary.current_branch || "N/A";
      filesChangedCount.value = summary.files_changed_count;
      summaryError.value = null;
    } catch (err) {
      summaryError.value = err.response?.data?.detail || "Failed to connect";
      console.error("StatusStore: Failed to fetch git status summary:", err);
    } finally {
      isLoadingSummary.value = false;
    }
  }

  function openNoteInEditor(path) {
    const title = path.replace(/\.md$/, "");
    router.push({ name: "note", params: { title } });
  }

  function clearCommitMessage() {
    commitMessage.value = "";
  }

  function initialize() {
    isLoading.value = true;
    isLoadingSummary.value = true;

    // Fetch initial state once
    gitApi.getGitStatus().then((data) => {
      gitStatus.value = data;
      branchName.value = data.current_branch || "N/A";
      filesChangedCount.value = data.files.length;
      isLoading.value = false;
      isLoadingSummary.value = false;
    });

    const eventSource = connectToGitEvents();

    // This listener updates the detailed file list directly
    eventSource.addEventListener("status_update", (event) => {
      console.log("Received full status_update event.");
      const fullStatus = JSON.parse(event.data);
      gitStatus.value = fullStatus;
      isLoading.value = false;
    });

    // This listener updates the summary indicator
    eventSource.addEventListener("summary_update", (event) => {
      console.log("Received summary_update event.");
      const summary = JSON.parse(event.data);
      branchName.value = summary.current_branch || "N/A";
      filesChangedCount.value = summary.files_changed_count;
      summaryError.value = null;
      isLoadingSummary.value = false;
    });

    eventSource.addEventListener("open", () => {
      console.log("SSE connection for status updates opened.");
      summaryError.value = null;
    });

    eventSource.addEventListener("error", () => {
      summaryError.value = "Real-time connection lost.";
    });
  }

  function cleanup() {
    // Cleanup is now handled globally in the eventSource module if needed,
    // but typically the connection lives as long as the app.
  }

  return {
    // State
    gitStatus,
    commitMessage,
    isLoading,
    isLoadingSummary,
    summaryError,
    branchName,
    filesChangedCount,
    // Getters
    stagedFiles,
    unstagedFiles,
    tooltipText,
    // Actions
    fetchStatus,
    fetchStatusSummary,
    openNoteInEditor,
    clearCommitMessage,
    initialize,
    cleanup,
  };
});
