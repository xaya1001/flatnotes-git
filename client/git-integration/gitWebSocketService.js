// client/git-integration/gitWebSocketService.js
import { useStatusStore } from "./stores/statusStore";

let socket = null;
let reconnectInterval = 5000; // 5-second reconnect interval
let reconnectTimer = null;

// --- START: Fallback Polling Logic ---
let pollingIntervalId = null;
const POLLING_FALLBACK_INTERVAL = 30000; // Poll every 30 seconds as a fallback

function startPollingFallback() {
  // Prevent multiple polling intervals from running
  if (pollingIntervalId) {
    return;
  }
  console.warn(
    `WebSocket connection failed. Falling back to polling every ${
      POLLING_FALLBACK_INTERVAL / 1000
    } seconds.`,
  );
  const statusStore = useStatusStore();
  // Fetch status immediately on fallback start
  statusStore.fetchStatus();
  pollingIntervalId = setInterval(() => {
    // We only poll if the document is visible to save resources,
    // complementing the existing visibilitychange handler in App.vue
    if (!document.hidden) {
      console.log("Polling for status update (fallback)...");
      statusStore.fetchStatus();
    }
  }, POLLING_FALLBACK_INTERVAL);
}

function stopPollingFallback() {
  if (pollingIntervalId) {
    console.log("WebSocket connected. Stopping polling fallback.");
    clearInterval(pollingIntervalId);
    pollingIntervalId = null;
  }
}
// --- END: Fallback Polling Logic ---

function connect() {
  // Prevent multiple connection attempts
  if (socket || reconnectTimer) {
    return;
  }

  // Ensure any previous polling is stopped before a new attempt
  stopPollingFallback();

  // Use the URL constructor for robust path joining. This is the safest way.
  const base = `${window.location.protocol}//${window.location.host}`;
  const path = new URL(import.meta.env.BASE_URL, base).pathname;

  // Create a clean base URL for the WebSocket path
  const wsPath = (path === "/" ? "" : path) + "/api/git/ws/status";

  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${window.location.host}${wsPath}`;

  console.log(`Attempting to connect to WebSocket at: ${wsUrl}`); // Added for easier debugging
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("WebSocket connection established.");
    // Stop fallback and clear reconnect timer on success
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    stopPollingFallback();
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "status_update") {
        console.log("WebSocket: Received status update trigger.");
        const statusStore = useStatusStore();
        statusStore.fetchStatus();
      }
    } catch (e) {
      console.error("WebSocket: Error parsing message data.", e);
    }
  };

  socket.onclose = () => {
    console.warn(
      `WebSocket disconnected. Attempting to reconnect in ${
        reconnectInterval / 1000
      }s...`,
    );
    socket = null;

    // Start polling and schedule reconnection
    startPollingFallback(); // Start fallback immediately

    // Don't create multiple reconnect timers
    if (!reconnectTimer) {
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        connect();
      }, reconnectInterval);
    }
  };

  socket.onerror = (error) => {
    console.error("WebSocket error:", error);
    // Let onclose handle the reconnection and fallback logic
    if (socket) {
      socket.close();
    }
  };
}

function disconnect() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  // Ensure polling is stopped on intentional disconnect
  stopPollingFallback();

  if (socket) {
    socket.onclose = null;
    socket.close();
    socket = null;
    console.log("WebSocket connection intentionally disconnected.");
  }
}

export const gitWebSocketService = {
  connect,
  disconnect,
};
