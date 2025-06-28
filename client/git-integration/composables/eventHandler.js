// /client/git-integration/composables/eventHandler.js
import eventBus from "../services/eventBus";
import { useStatusStore } from "../stores/statusStore";

export function initializeGitEventHandlers() {
  eventBus.on("note:saved", () => {
    const statusStore = useStatusStore();
    statusStore.fetchStatus();
  });

  eventBus.on("note:deleted", () => {
    const statusStore = useStatusStore();
    statusStore.fetchStatus();
  });
}
