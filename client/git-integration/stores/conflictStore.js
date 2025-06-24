// client/git-integration/stores/conflictStore.js (FIXED)
import { defineStore } from "pinia";
import { useToast } from "primevue/usetoast";
import { v4 as uuidv4 } from "uuid";
import * as gitApi from "../gitApi";
import eventBus from "../eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";
import { useActionsStore } from "./actionsStore";

export const useConflictStore = defineStore("git-conflict", () => {
  const toast = useToast();

  async function handleContinue() {
    const actionsStore = useActionsStore();
    actionsStore.isActionLoading = true;
    const operationId = uuidv4();
    const actionName = "Continue Operation";
    eventBus.emit(GIT_OPERATION.WILL_START, { actionName, operationId });

    try {
      const response = await gitApi.gitConflictContinue();
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
      throw err;
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
      eventBus.emit(GIT_CONFLICT.RESOLVED, {
        actionName,
        operationId,
        response,
      });
    } catch (err) {
      eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
      throw err;
    } finally {
      actionsStore.isActionLoading = false;
    }
  }

  return {
    handleContinue,
    handleAbort,
  };
});
