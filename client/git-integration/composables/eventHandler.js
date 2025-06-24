// /client/git-integration/composables/eventHandler.js
import eventBus from "../eventBus";
import { useStatusStore } from "../stores/statusStore";

export function initializeGitEventHandlers() {
  const statusStore = useStatusStore();

  eventBus.on("note:saved", () => {
    statusStore.fetchStatus();
  });

  eventBus.on("note:deleted", () => {
    statusStore.fetchStatus();
  });
}
