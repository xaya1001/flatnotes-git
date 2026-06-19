// /client/git-integration/composables/eventHandler.js
import eventBus from "../services/eventBus";
import { useStatusStore } from "../stores/statusStore";

let initialized = false;

function refreshStatus() {
  const statusStore = useStatusStore();
  statusStore.fetchStatus();
}

export function initializeGitEventHandlers() {
  if (initialized) return;
  initialized = true;

  eventBus.on("note:saved", refreshStatus);
  eventBus.on("note:deleted", refreshStatus);
}

export function cleanupGitEventHandlers() {
  if (!initialized) return;
  initialized = false;

  eventBus.off("note:saved", refreshStatus);
  eventBus.off("note:deleted", refreshStatus);
}
