// client/git-integration/composables/useGitOperation.js
import { ref } from "vue";
import { v4 as uuidv4 } from "uuid";
import eventBus from "../services/eventBus";
import { GIT_OPERATION, GIT_CONFLICT } from "../events";
import { useToast } from "primevue/usetoast";

export function useGitOperation(actionName, operationFunc) {
  const isLoading = ref(false);
  const error = ref(null);
  const data = ref(null);
  const toast = useToast();

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
      const statusCode = err.response?.status;

      if (statusCode === 401 && errorData?.state === "AUTHENTICATION_FAILED") {
        toast.add({
          severity: "error",
          summary: "Git Authentication Failed",
          detail:
            "Could not connect to the remote repository. This is likely due to an incorrect remote URL (HTTPS instead of SSH) or misconfigured SSH keys on the server. Please check your setup guide.",
          life: 20000,
        });
        eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
      } else if (statusCode === 409 && errorData?.state?.includes("CONFLICT")) {
        eventBus.emit(GIT_CONFLICT.DETECTED, { operationId, errorData });
      } else {
        eventBus.emit(GIT_OPERATION.DID_FAIL, { actionName, operationId, err });
      }

      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  return { isLoading, error, data, execute };
}
