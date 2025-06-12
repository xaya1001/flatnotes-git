// client/git-integration/stores/historyStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import { useRouter } from "vue-router";
import * as gitApi from "../gitApi";

/**
 * Manages the state related to `git log` and commit history browsing.
 */
export const useHistoryStore = defineStore("git-history", () => {
  // -- DEPS --
  const toast = useToast();
  const router = useRouter();

  // -- STATE --
  const gitLog = ref([]);
  const isLoading = ref(false);
  const commitFilesCache = ref({});
  const expandedCommit = ref(null);
  const isFilesLoading = ref(false);

  // -- ACTIONS --
  async function fetchGitLog() {
    isLoading.value = true;
    try {
      const response = await gitApi.getGitLog(20, 1);
      gitLog.value = response.log;
    } catch (err) {
      toast.add({
        severity: "error",
        summary: "Error Fetching Log",
        detail: err.message,
        life: 3000,
      });
      gitLog.value = [];
    } finally {
      isLoading.value = false;
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
        commitFilesCache.value[commitHash] = []; // Store empty on error
      } finally {
        isFilesLoading.value = false;
      }
    }
  }

  function openNoteInEditor(path) {
    const title = path.replace(/\.md$/, "");
    router.push({ name: "note", params: { title } });
  }

  return {
    // State
    gitLog,
    isLoading,
    commitFilesCache,
    expandedCommit,
    isFilesLoading,
    // Actions
    fetchGitLog,
    toggleCommitExpansion,
    openNoteInEditor,
  };
});
