// client/git-integration/composables/useGitOperation.js
import { ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import eventBus from "../services/eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";

export function useGitOperation(actionName, operationFunc) {
  const isLoading = ref(false);
  const error = ref(null);
  const data = ref(null);

  const execute = async (...args) => {
    isLoading.value = true;
    error.value = null;
    data.value = null;
    const operationId = uuidv4();
    eventBus.emit(GIT_OPERATION.WILL_START, { actionName, operationId });

    try {
      const response = await operationFunc(...args);
      data.value = response;
      eventBus.emit(GIT_OPERATION.DID_SUCCEED, {
        actionName,
        operationId,
        response,
      });
      return response;
    } catch (err) {
      error.value = err;
      const errorData = err.response?.data?.detail;
      if (
        err.response?.status === 409 &&
        errorData?.state?.includes("CONFLICT")
      ) {
        eventBus.emit(GIT_CONFLICT.DETECTED, { operationId, errorData });
      } else {
        eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
      }
      throw err; // Re-throw so the component can catch it if needed.
    } finally {
      isLoading.value = false;
    }
  };

  return { isLoading, error, data, execute };
}
