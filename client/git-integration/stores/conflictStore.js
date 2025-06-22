// client/git-integration/stores/conflictStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useToast } from "primevue/usetoast";
import { v4 as uuidv4 } from "uuid";
import * as gitApi from "../gitApi";
import eventBus from "../eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";
import { useActionsStore } from "./actionsStore";

export const useConflictStore = defineStore("git-conflict", () => {
  const toast = useToast();

  const isInConflict = ref(false);
  const conflictedFiles = ref([]);

  function enterConflictMode(errorData, options = {}) {
    isInConflict.value = true;
    conflictedFiles.value = errorData.conflicted_files || [];

    const conflictType = errorData.state.includes("REBASING")
      ? "Rebase"
      : "Merge";

    if (!options.silent) {
      toast.add({
        severity: "warn",
        summary: `Sync Conflict: ${conflictType}`,
        detail: "Please resolve the file conflicts to continue.",
        life: 6000,
      });
    }
  }

  function exitConflictMode() {
    isInConflict.value = false;
    conflictedFiles.value = [];
  }

  async function handleContinue() {
    const actionsStore = useActionsStore();
    actionsStore.isActionLoading = true;
    const operationId = uuidv4();
    const actionName = "Continue Operation";
    eventBus.emit(GIT_OPERATION.WILL_START, { actionName, operationId });

    try {
      const response = await gitApi.gitConflictContinue();
      exitConflictMode();
      eventBus.emit(GIT_CONFLICT.RESOLVED, {
        actionName,
        operationId,
        response,
      });
    } catch (err) {
      const errorData = err.response?.data?.detail;
      if (err.response?.status === 409 && errorData?.state) {
        eventBus.emit(GIT_CONFLICT.DETECTED, { operationId, errorData });
      } else {
        eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
      }
    } finally {
      actionsStore.isActionLoading = false;
    }
  }

  async function handleAbort() {
    const actionsStore = useActionsStore();
    actionsStore.isActionLoading = true;
    const operationId = uuidv4();
    const actionName = "Abort Operation";
    eventBus.emit(GIT_OPERATION.WILL_START, { actionName, operationId });

    try {
      const response = await gitApi.gitConflictAbort();
      exitConflictMode();
      eventBus.emit(GIT_CONFLICT.RESOLVED, {
        actionName,
        operationId,
        response,
      });
    } catch (err) {
      eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
    } finally {
      actionsStore.isActionLoading = false;
    }
  }

  // --- Event Listeners ---
  eventBus.on(GIT_CONFLICT.DETECTED, (payload) => {
    enterConflictMode(payload.errorData);
  });

  return {
    isInConflict,
    conflictedFiles,
    enterConflictMode,
    exitConflictMode,
    handleContinue,
    handleAbort,
  };
});
