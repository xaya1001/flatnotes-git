// /client/git-integration/composables/useGitIntegration.js
import { computed, onMounted, onUnmounted } from "vue";
import { useGlobalStore } from "../../globalStore";
import { useStatusStore } from "../stores/statusStore";
import { useLogStore } from "../stores/logStore";
import { gitWebSocketService } from "../gitWebSocketService.js";
import { initializeGitEventHandlers } from "./eventHandler";

export function useGitIntegration() {
  const globalStore = useGlobalStore();
  const statusStore = useStatusStore();
  const logStore = useLogStore();

  const gitEnabled = computed(
    () => globalStore.config.value?.flatnotesGitEnabled,
  );

  function onVisibilityChange() {
    if (!document.hidden && gitEnabled.value) {
      statusStore.fetchStatus();
    }
  }

  onMounted(() => {
    if (!gitEnabled.value) return;

    statusStore.fetchStatus();
    logStore.initialize();
    gitWebSocketService.connect();
    initializeGitEventHandlers();
    document.addEventListener("visibilitychange", onVisibilityChange);
  });

  onUnmounted(() => {
    if (!gitEnabled.value) return;

    gitWebSocketService.disconnect();
    document.removeEventListener("visibilitychange", onVisibilityChange);
  });
}
