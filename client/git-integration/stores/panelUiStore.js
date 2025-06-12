// client/git-integration/stores/panelUiStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useLogStore } from "./logStore";

/**
 * Manages the UI state of the GitPanel itself, such as visibility,
 * pinning, and the confirmation modal.
 */
export const usePanelUiStore = defineStore("git-panel-ui", () => {
  // -- STATE --
  const isVisible = ref(false);
  const isPinned = ref(false);

  // Confirmation Modal State
  const isConfirmModalVisible = ref(false);
  const confirmModalProps = ref({});
  let confirmModalResolve = null;

  // -- ACTIONS --
  function showPanel() {
    isVisible.value = true;
  }

  function hidePanel() {
    isVisible.value = false;
  }

  function toggleVisibility() {
    isVisible.value = !isVisible.value;
  }

  function togglePin() {
    isPinned.value = !isPinned.value;
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
          const logStore = useLogStore();
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

  return {
    isVisible,
    isPinned,
    isConfirmModalVisible,
    confirmModalProps,
    showPanel,
    hidePanel,
    toggleVisibility,
    togglePin,
    showConfirmation,
    resolveConfirmation,
  };
});
