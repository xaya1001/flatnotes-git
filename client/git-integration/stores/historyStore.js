// client/git-integration/stores/historyStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import * as gitApi from "../gitApi";
import eventBus from "../eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";

export const useHistoryStore = defineStore("git-history", () => {
  const toast = useToast();
  const router = useRouter();

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

  // --- Event Listeners ---
  const refreshEvents = [GIT_OPERATION.DID_SUCCEED, GIT_CONFLICT.RESOLVED];
  refreshEvents.forEach((eventName) => {
    eventBus.on(eventName, (payload) => {
      // Only refresh on actions that change history
      const relevantActions = [
        "Commit & Sync",
        "Pull",
        "Push",
        "Commit",
        "Continue Operation",
        "Abort Operation",
        "Switch Branch",
        "Reset to Remote",
      ];
      if (relevantActions.includes(payload.actionName)) {
        fetchGitLog();
      }
    });
  });

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
  };
});
