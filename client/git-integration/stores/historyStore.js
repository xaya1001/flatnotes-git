// client/git-integration/stores/historyStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import * as gitApi from "../gitApi";
import { useActionsStore } from "./actionsStore";
import { usePanelUiStore } from "./panelUiStore";
import { useLogStore } from "./logStore";
import { useStatusStore } from "./statusStore";

export const useHistoryStore = defineStore("git-history", () => {
  const toast = useToast();
  const router = useRouter();
  const panelUiStore = usePanelUiStore();
  const logStore = useLogStore();
  const statusStore = useStatusStore();

  const gitLog = ref([]);
  const isLoading = ref(false);
  const remoteBaseUrl = ref(null);
  const commitFilesCache = ref({});
  const expandedCommit = ref(null);
  const isFilesLoading = ref(false);

  async function fetchGitLog() {
    isLoading.value = true;
    try {
      const response = await gitApi.getGitLog(20, 1);
      gitLog.value = response.log;
      remoteBaseUrl.value = response.remote_base_url;
    } catch (err) {
      toast.add({
        severity: "error",
        summary: "Error Fetching Log",
        detail: err.message,
        life: 3000,
      });
      gitLog.value = [];
      remoteBaseUrl.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  async function toggleCommitExpansion(commitHash) {
    if (expandedCommit.value === commitHash) {
      expandedCommit.value = null;
      return;
    }
    expandedCommit.value = commitHash;
    if (!commitFilesCache.value[commitHash]) {
      isFilesLoading.value = true;
      try {
        commitFilesCache.value[commitHash] =
          await gitApi.getGitCommitFiles(commitHash);
      } catch (err) {
        toast.add({
          severity: "error",
          summary: "Error Fetching Commit Files",
          detail: err.message,
          life: 3000,
        });
        commitFilesCache.value[commitHash] = [];
      } finally {
        isFilesLoading.value = false;
      }
    }
  }

  function openNoteInEditor(path) {
    const title = path.replace(/\.md$/, "");
    router.push({ name: "note", params: { title } });
  }

  async function restoreFile(commitHash, filepath) {
    const actionsStore = useActionsStore();

    const confirmed = await panelUiStore.showConfirmation({
      title: "Confirm File Restore",
      message: `This will overwrite your current version of '${filepath}' with the version from commit ${commitHash.substring(0, 7)}. This cannot be undone. Are you sure?`,
      confirmButtonText: "Yes, Restore File",
      confirmButtonStyle: "danger",
    });

    if (confirmed) {
      actionsStore.isActionLoading = true;
      const pendingLogId = logStore.addPendingLog(`Restoring '${filepath}'...`);
      try {
        await gitApi.gitRestoreFile(commitHash, filepath);

        toast.add({
          severity: "success",
          summary: "Success",
          detail: `File '${filepath}' restored.`,
          life: 3000,
        });
        logStore.updateLog(pendingLogId, {
          level: "success",
          message: `File '${filepath}' restored.`,
        });

        await statusStore.fetchStatus();
        await statusStore.fetchStatusSummary();
      } catch (err) {
        const errorMessage = err.response?.data?.detail || err.message;
        toast.add({
          severity: "error",
          summary: "Error Restoring File",
          detail: errorMessage,
          life: 5000,
        });
        logStore.updateLog(pendingLogId, {
          level: "error",
          message: `Failed to restore '${filepath}'.`,
          details: errorMessage,
        });
      } finally {
        actionsStore.isActionLoading = false;
      }
    }
  }

  return {
    gitLog,
    isLoading,
    remoteBaseUrl,
    commitFilesCache,
    expandedCommit,
    isFilesLoading,
    fetchGitLog,
    toggleCommitExpansion,
    openNoteInEditor,
    restoreFile,
  };
});
