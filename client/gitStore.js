// client/stores/gitStore.js
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import { useLogStore } from "./logStore";
import * as api from "./api";
import { useGlobalStore } from "./globalStore";

export const useGitStore = defineStore("git-panel", () => {
  // Dependencies
  const toast = useToast();
  const router = useRouter();
  const logStore = useLogStore();

  // --- STATE ---
  const isActionLoading = ref(false);
  const isRefreshing = ref(false);
  const currentAction = ref("");
  const gitStatus = ref({ files: [] });
  const gitLog = ref([]);
  const commitMessage = ref("");
  const isPinned = ref(false);
  const isAutoSyncPaused = ref(false);
  let logPollInterval = null;
  let summaryPollInterval = null;
  const commitFilesCache = ref({});
  const expandedCommit = ref(null);

  // State for GitStatusIndicator
  const isLoadingSummary = ref(true);
  const summaryError = ref(null);
  const branchName = ref("");
  const filesChangedCount = ref(0);

  // Confirmation Modal State
  const isConfirmModalVisible = ref(false);
  const confirmModalProps = ref({});
  let confirmModalResolve = null;

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
    if (isLoadingSummary.value) return "Loading Git status...";
    if (summaryError.value) return `Error: ${summaryError.value}`;
    if (filesChangedCount.value > 0)
      return `${filesChangedCount.value} changes detected on branch '${branchName.value}'. Click to view.`;
    return `On branch '${branchName.value}'. Synced.`;
  });

  // --- ACTIONS ---

  // UI Actions
  function togglePin() {
    isPinned.value = !isPinned.value;
  }

  function openNoteInEditor(path) {
    const title = path.replace(/\.md$/, "");
    router.push({ name: "note", params: { title } });
  }

  function showConfirmation(props) {
    return new Promise((resolve) => {
      confirmModalProps.value = {
        title: props.title,
        message: props.message,
        confirmButtonText: props.confirmButtonText || "Confirm",
        confirmButtonStyle: props.confirmButtonStyle || "danger",
      };
      isConfirmModalVisible.value = true;
      confirmModalResolve = (result) => {
        isConfirmModalVisible.value = false;
        if (!result) {
          logStore.addLog({
            level: "info",
            message: `${props.title}: Operation cancelled by user.`,
          });
        }
        resolve(result);
      };
    });
  }

  function resolveConfirmation(result) {
    if (confirmModalResolve) {
      confirmModalResolve(result);
    }
  }

  // Data Fetching Actions
  async function fetchStatusSummary() {
    try {
      const summary = await api.getGitStatusSummary();
      branchName.value = summary.current_branch || "N/A";
      filesChangedCount.value = summary.files_changed_count;
      summaryError.value = null;
    } catch (err) {
      summaryError.value = err.response?.data?.detail || "Failed to connect";
      console.error("GitStore: Failed to fetch git status summary:", err);
    } finally {
      isLoadingSummary.value = false;
    }
  }

  async function performFetchStatus() {
    currentAction.value = "status";
    gitStatus.value = { files: [] };
    try {
      gitStatus.value = await api.getGitStatus();
    } catch (err) {
      toast.add({
        severity: "error",
        summary: "Error Fetching Status",
        detail: err.message,
        life: 3000,
      });
    } finally {
      currentAction.value = "";
    }
  }

  async function fetchGitLog() {
    currentAction.value = "log";
    gitLog.value = [];
    try {
      const response = await api.getGitLog(20, 1);
      gitLog.value = response.log;
    } catch (err) {
      toast.add({
        severity: "error",
        summary: "Error Fetching Log",
        detail: err.message,
        life: 3000,
      });
    } finally {
      currentAction.value = "";
    }
  }

  async function fetchActivityLog() {
    try {
      const backendLogs = await api.getGitActivityLog();
      logStore.mergeBackendLogs(backendLogs);
    } catch (error) {
      console.error("Failed to fetch activity log from backend:", error);
    }
  }

  async function refreshAll() {
    isRefreshing.value = true;
    const pendingLogId = logStore.addPendingLog("Refreshing all data...");
    await Promise.all([
      performFetchStatus(),
      fetchGitLog(),
      fetchActivityLog(),
      fetchStatusSummary(),
    ]);
    logStore.updateLog(pendingLogId, {
      level: "success",
      message: "All data refreshed.",
      details: null,
    });
    isRefreshing.value = false;
  }

  // Core Action Wrapper
  async function performGitAction(
    actionFunc,
    args,
    actionName,
    successMessage,
  ) {
    isActionLoading.value = true;
    const pendingLogId = logStore.addPendingLog(`${actionName}...`);
    try {
      const response = await actionFunc(...args);
      toast.add({
        severity: "success",
        summary: "Success",
        detail: successMessage,
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: successMessage,
        details: response.stdout || response.message || null,
      });
      // Refresh both detailed panel and summary indicator after any action
      await performFetchStatus();
      await fetchStatusSummary();
      if (
        actionName.includes("Commit") ||
        actionName.includes("Sync") ||
        actionName.includes("Pull")
      ) {
        await fetchGitLog();
      }
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message;
      toast.add({
        severity: "error",
        summary: `Error: ${actionName}`,
        detail: errorMessage,
        life: 5000,
      });
      logStore.updateLog(pendingLogId, {
        level: "error",
        message: `Failed: ${actionName}`,
        details: errorMessage,
      });
    } finally {
      isActionLoading.value = false;
    }
  }

  // Individual Git Actions
  function handleStageFile(filepath) {
    performGitAction(
      api.gitStageFile,
      [filepath],
      "Stage File",
      `File '${filepath}' staged.`,
    );
  }
  function handleStageAll() {
    performGitAction(api.gitAddAll, [], "Stage All", "All changes staged.");
  }
  function handleUnstageFile(filepath) {
    performGitAction(
      api.gitUnstageFile,
      [filepath],
      "Unstage File",
      `File '${filepath}' unstaged.`,
    );
  }
  function handleUnstageAll() {
    performGitAction(
      api.gitUnstageAll,
      [],
      "Unstage All",
      "All staged changes unstaged.",
    );
  }
  async function handleDiscardFile(filepath) {
    const confirmed = await showConfirmation({
      title: "Confirm Discard",
      message: `Discard changes to '${filepath}'? This cannot be undone.`,
      confirmButtonText: "Discard",
    });
    if (confirmed) {
      performGitAction(
        api.gitDiscardFile,
        [filepath],
        "Discard File",
        `Changes to '${filepath}' discarded.`,
      );
    }
  }
  async function handleDiscardAll() {
    const confirmed = await showConfirmation({
      title: "Confirm Discard All",
      message: `Discard ALL unstaged changes? This will delete new files and cannot be undone.`,
      confirmButtonText: "Discard All",
    });
    if (confirmed) {
      performGitAction(
        api.gitDiscardAll,
        [],
        "Discard All",
        "All unstaged changes discarded.",
      );
    }
  }
  function handleCommit() {
    if (!commitMessage.value.trim()) return;
    performGitAction(
      api.gitCommit,
      [commitMessage.value],
      "Commit",
      "Changes committed.",
    );
    commitMessage.value = "";
  }
  function handleSync() {
    performGitAction(
      api.gitSyncWorkspace,
      [commitMessage.value],
      "Commit & Sync",
      "Workspace synced.",
    );
    commitMessage.value = "";
  }
  function handlePull() {
    performGitAction(api.gitPull, [], "Pull", "Pull operation completed.");
  }
  function handlePush() {
    performGitAction(api.gitPush, [], "Push", "Push operation completed.");
  }
  async function toggleAutoSyncPause() {
    const action = isAutoSyncPaused.value
      ? api.resumeAutoSync
      : api.pauseAutoSync;
    const actionName = isAutoSyncPaused.value
      ? "Resume Auto-Sync"
      : "Pause Auto-Sync";
    const successMessage = `Auto-sync ${isAutoSyncPaused.value ? "resumed" : "paused"}.`;
    isActionLoading.value = true;
    const pendingLogId = logStore.addPendingLog(`${actionName}...`);
    try {
      const response = await action();
      isAutoSyncPaused.value = response.paused;
      toast.add({
        severity: "info",
        summary: "Auto-Sync",
        detail: successMessage,
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "success",
        message: successMessage,
      });
    } catch (err) {
      const errorMessage =
        err.response?.data?.detail || "Failed to update auto-sync state.";
      toast.add({
        severity: "error",
        summary: "Error",
        detail: errorMessage,
        life: 3000,
      });
      logStore.updateLog(pendingLogId, {
        level: "error",
        message: `Failed: ${actionName}`,
        details: errorMessage,
      });
    } finally {
      isActionLoading.value = false;
    }
  }

  async function toggleCommitExpansion(commitHash) {
    if (expandedCommit.value === commitHash) {
      expandedCommit.value = null; // Collapse if already open
      return;
    }

    expandedCommit.value = commitHash; // Expand the new one

    // Fetch files if not already in cache
    if (!commitFilesCache.value[commitHash]) {
      isActionLoading.value = true; // Use a general loading state
      try {
        commitFilesCache.value[commitHash] =
          await api.getGitCommitFiles(commitHash);
      } catch (err) {
        toast.add({
          severity: "error",
          summary: "Error Fetching Commit Files",
          detail: err.message,
          life: 3000,
        });
        commitFilesCache.value[commitHash] = []; // Store empty on error to prevent re-fetch
      } finally {
        isActionLoading.value = false;
      }
    }
  }

  // Store Lifecycle
  async function initialize() {
    isLoadingSummary.value = true;
    await refreshAll();
    const config = useGlobalStore().config.value;
    if (config.flatnotesGitAutoSyncInterval > 0) {
      try {
        const state = await api.getAutoSyncState();
        isAutoSyncPaused.value = state.paused;
      } catch (error) {
        console.error("Failed to get initial auto-sync state", error);
      }
    }
    logPollInterval = setInterval(fetchActivityLog, 10000);
    summaryPollInterval = setInterval(fetchStatusSummary, 30000);
  }

  function cleanup() {
    if (logPollInterval) clearInterval(logPollInterval);
    if (summaryPollInterval) clearInterval(summaryPollInterval);
  }

  // Expose state, getters, and actions
  return {
    isActionLoading,
    isRefreshing,
    currentAction,
    gitStatus,
    gitLog,
    commitMessage,
    isPinned,
    isAutoSyncPaused,
    isConfirmModalVisible,
    confirmModalProps,
    isLoadingSummary,
    summaryError,
    branchName,
    filesChangedCount,
    stagedFiles,
    unstagedFiles,
    tooltipText,
    togglePin,
    openNoteInEditor,
    showConfirmation,
    resolveConfirmation,
    refreshAll,
    handleStageFile,
    handleStageAll,
    handleUnstageFile,
    handleUnstageAll,
    handleDiscardFile,
    handleDiscardAll,
    handleCommit,
    handleSync,
    handlePull,
    handlePush,
    toggleAutoSyncPause,
    commitFilesCache,
    expandedCommit,
    toggleCommitExpansion,
    initialize,
    cleanup,
  };
});
