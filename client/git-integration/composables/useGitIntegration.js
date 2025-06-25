// /client/git-integration/composables/useGitIntegration.js
import { computed, watchEffect } from "vue";
import { useGlobalStore } from "../../globalStore";
import { useStatusStore } from "../stores/statusStore";
import { gitWebSocketService } from "../gitWebSocketService.js";
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
      gitWebSocketService.connect();
      initializeGitEventHandlers();
      document.addEventListener("visibilitychange", onVisibilityChange);

      onCleanup(() => {
        gitWebSocketService.disconnect();
        document.removeEventListener("visibilitychange", onVisibilityChange);
      });
    }
  });
}
