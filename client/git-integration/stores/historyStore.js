// client/git-integration/stores/historyStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import * as gitApi from "../gitApi";
import eventBus from "../services/eventBus";
import { GIT_OPERATION } from "../events";

export const useHistoryStore = defineStore("git-history", () => {
  const toast = useToast();
  const router = useRouter();

  const gitLog = ref([]);
  const isLoading = ref(false);
  const remoteBaseUrl = ref(null);
  const commitFilesCache = ref({});
  const expandedCommit = ref(null);
  const isFilesLoading = ref(false);

  // --- state for pagination ---
  const isLoadingMore = ref(false);
  const currentPage = ref(1);
  const hasMoreCommits = ref(true);
  const PAGE_SIZE = 20;

  async function fetchGitLog() {
    isLoading.value = true;
    currentPage.value = 1;
    hasMoreCommits.value = true; // Reset on refresh
    try {
      const response = await gitApi.getGitLog(PAGE_SIZE, currentPage.value);
      gitLog.value = response.log;
      remoteBaseUrl.value = response.remote_base_url;
      // If fewer than PAGE_SIZE logs are returned, we've reached the end.
      if (response.log.length < PAGE_SIZE) {
        hasMoreCommits.value = false;
      }
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

  async function fetchMoreCommits() {
    if (isLoadingMore.value || !hasMoreCommits.value) return;

    isLoadingMore.value = true;
    try {
      const nextPage = currentPage.value + 1;
      const response = await gitApi.getGitLog(PAGE_SIZE, nextPage);
      gitLog.value.push(...response.log);
      currentPage.value = nextPage;
      if (response.log.length < PAGE_SIZE) {
        hasMoreCommits.value = false;
      }
    } catch (err) {
      toast.add({
        severity: "error",
        summary: "Error Fetching More Commits",
        detail: err.message,
        life: 3000,
      });
      // Do not increment page on failure to allow retry
    } finally {
      isLoadingMore.value = false;
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

  // --- Event Listener ---
  eventBus.on(GIT_OPERATION.DID_SUCCEED, (payload) => {
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

  return {
    gitLog,
    isLoading,
    remoteBaseUrl,
    commitFilesCache,
    expandedCommit,
    isFilesLoading,
    isLoadingMore,
    hasMoreCommits,
    fetchGitLog,
    fetchMoreCommits,
    toggleCommitExpansion,
    openNoteInEditor,
  };
});
