// /client/git-integration/composables/useGitIntegration.js
import { computed, watchEffect } from "vue";
import { useGlobalStore } from "../../globalStore";
import { useStatusStore } from "../stores/statusStore";
import { webSocket } from "../services/webSocket.js";
import { initializeGitEventHandlers } from "./eventHandler";

export function useGitIntegration() {
  const globalStore = useGlobalStore();
  const statusStore = useStatusStore();

  const gitEnabled = computed(
    () => globalStore.config.value?.flatnotesGitEnabled,
  );

  function onVisibilityChange() {
    if (!document.hidden && gitEnabled.value) {
      statusStore.fetchStatus();
    }
  }

  watchEffect((onCleanup) => {
    if (gitEnabled.value) {
      webSocket.connect();
      initializeGitEventHandlers();
      document.addEventListener("visibilitychange", onVisibilityChange);

      onCleanup(() => {
        webSocket.disconnect();
        document.removeEventListener("visibilitychange", onVisibilityChange);
      });
    }
  });
}
