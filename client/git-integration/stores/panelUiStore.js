// client/git-integration/stores/panelUiStore.js
import { defineStore } from "pinia";
import { ref } from "vue";
import { useLogStore } from "./logStore";

export const usePanelUiStore = defineStore("git-panel-ui", () => {
  // -- STATE --
  const isSidebarVisible = ref(false);
  const isPinned = ref(false);
  const width = ref(480); // Default width in pixels

  // Confirmation Modal State
  const isConfirmModalVisible = ref(false);
  const confirmModalProps = ref({});
  let confirmModalResolve = null;

  // -- ACTIONS --

  function toggleSidebar() {
    isSidebarVisible.value = !isSidebarVisible.value;
  }

  function hideSidebar() {
    if (!isPinned.value) {
      isSidebarVisible.value = false;
    }
  }

  function togglePin() {
    isPinned.value = !isPinned.value;
  }

  function setWidth(newWidth) {
    const minWidth = 320;
    const maxWidth = 900;
    width.value = Math.max(minWidth, Math.min(newWidth, maxWidth));
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
    isSidebarVisible,
    isPinned,
    width,
    isConfirmModalVisible,
    confirmModalProps,
    toggleSidebar,
    hideSidebar,
    togglePin,
    setWidth,
    showConfirmation,
    resolveConfirmation,
  };
});
