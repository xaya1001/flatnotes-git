// client/git-integration/stores/actionsStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import * as gitApi from "../gitApi";
import eventBus from "../eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";

export const useActionsStore = defineStore("git-actions", () => {
  const isActionLoading = ref(false);
  const isAutoSyncPaused = ref(false);

  async function performGitAction(actionFunc, args, actionName) {
    isActionLoading.value = true;
    const operationId = uuidv4();
    eventBus.emit(GIT_OPERATION.WILL_START, { actionName, operationId });

    try {
      const response = await actionFunc(...args);
      eventBus.emit(GIT_OPERATION.DID_SUCCEED, {
        actionName,
        operationId,
        response,
      });
      return true;
    } catch (err) {
      eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
      return false;
    } finally {
      isActionLoading.value = false;
    }
  }

  async function handleComplexAction(actionFunc, args, actionName) {
    isActionLoading.value = true;
    const operationId = uuidv4();
    eventBus.emit(GIT_OPERATION.WILL_START, { actionName, operationId });

    try {
      const response = await actionFunc(...args);
      eventBus.emit(GIT_OPERATION.DID_SUCCEED, {
        actionName,
        operationId,
        response,
      });
      return true;
    } catch (err) {
      const errorData = err.response?.data?.detail;
      if (err.response?.status === 409 && errorData?.state) {
        if (errorData.state.includes("CONFLICT")) {
          eventBus.emit(GIT_CONFLICT.DETECTED, { operationId, errorData });
        } else {
          // Handle other specific 409s like non-fast-forward
          eventBus.emit(GIT_OPERATION.DID_FAIL, {
            actionName,
            operationId,
            err,
          });
        }
      } else {
        eventBus.emit(GIT_OPERATION.DID_FAIL, {
          actionName,
          operationId,
          err,
        });
      }
      return false;
    } finally {
      isActionLoading.value = false;
    }
  }

  function handleSync(message) {
    return handleComplexAction(
      gitApi.gitSyncWorkspace,
      [message],
      "Commit & Sync",
    );
  }

  function handlePull() {
    return handleComplexAction(gitApi.gitPull, [], "Pull");
  }

  function handleStageFile(filepath) {
    return performGitAction(
      gitApi.gitStageFile,
      [filepath],
      `Stage File: ${filepath.split("/").pop()}`,
    );
  }

  function handleStageAll() {
    return performGitAction(gitApi.gitAddAll, [], "Stage All");
  }

  function handleUnstageFile(filepath) {
    return performGitAction(
      gitApi.gitUnstageFile,
      [filepath],
      `Unstage File: ${filepath.split("/").pop()}`,
    );
  }

  function handleUnstageAll() {
    return performGitAction(gitApi.gitUnstageAll, [], "Unstage All");
  }

  function handleDiscardFile(filepath) {
    return performGitAction(
      gitApi.gitDiscardFile,
      [filepath],
      `Discard File: ${filepath.split("/").pop()}`,
    );
  }

  function handleDiscardAll() {
    return performGitAction(gitApi.gitDiscardAll, [], "Discard All");
  }

  function handleCommit(message) {
    return performGitAction(gitApi.gitCommit, [message], "Commit");
  }

  function handlePush() {
    return performGitAction(gitApi.gitPush, [], "Push");
  }

  async function fetchAutoSyncState() {
    try {
      const state = await gitApi.getAutoSyncState();
      isAutoSyncPaused.value = state.paused;
    } catch (error) {
      console.error("Failed to get initial auto-sync state", error);
    }
  }

  async function toggleAutoSyncPause() {
    const action = isAutoSyncPaused.value
      ? gitApi.resumeAutoSync
      : gitApi.pauseAutoSync;
    const actionName = isAutoSyncPaused.value
      ? "Resume Auto-Sync"
      : "Pause Auto-Sync";

    isActionLoading.value = true;
    const operationId = uuidv4();
    eventBus.emit(GIT_OPERATION.WILL_START, { actionName, operationId });

    try {
      const response = await action();
      isAutoSyncPaused.value = response.paused;
      eventBus.emit(GIT_OPERATION.DID_SUCCEED, {
        actionName,
        operationId,
        response,
      });
    } catch (err) {
      eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
    } finally {
      isActionLoading.value = false;
    }
  }

  async function getBranches() {
    try {
      return await gitApi.getBranches();
    } catch (error) {
      const operationId = uuidv4();
      eventBus.emit(GIT_OPERATION.WILL_START, {
        actionName: "Fetch Branches",
        operationId,
      });
      eventBus.emit(GIT_OPERATION.DID_FAIL, {
        actionName: "Fetch Branches",
        operationId,
        err: error,
      });
      return { branches: [], current_branch: "Error" };
    }
  }

  function switchBranch(branchName) {
    return performGitAction(gitApi.switchBranch, [branchName], "Switch Branch");
  }

  function handleResetToRemote() {
    return performGitAction(gitApi.gitResetToRemote, [], "Reset to Remote");
  }

  function handleRestoreFile(commitHash, filepath) {
    return performGitAction(
      gitApi.gitRestoreFile,
      [commitHash, filepath],
      "Restore File",
    );
  }

  return {
    isActionLoading,
    isAutoSyncPaused,
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
    fetchAutoSyncState,
    toggleAutoSyncPause,
    getBranches,
    switchBranch,
    handleResetToRemote,
    handleRestoreFile,
  };
});
