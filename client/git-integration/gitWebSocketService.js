// client/git-integration/gitWebSocketService.js
import { useStatusStore } from "./stores/statusStore";

let socket = null;
let reconnectInterval = 5000; // 5-second reconnect interval
let reconnectTimer = null;

function connect() {
  // Prevent multiple connection attempts
  if (socket || reconnectTimer) {
    return;
  }

  // Dynamically determine WebSocket protocol
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";

  // Use a relative URL to automatically adapt to any path_prefix
  const pathPrefix = import.meta.env.BASE_URL.replace(/\/$/, ""); // Get base URL from Vite config
  const wsUrl = `${protocol}//${window.location.host}${pathPrefix}/api/git/ws/status`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    console.log("WebSocket connection established.");
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "status_update") {
        console.log("WebSocket: Received status update trigger.");
        // Key logic: upon receiving a trigger, call the existing action to fetch the latest state.
        const statusStore = useStatusStore();
        statusStore.fetchStatus();
      }
    } catch (e) {
      console.error("WebSocket: Error parsing message data.", e);
    }
  };

  socket.onclose = () => {
    console.warn(
      `WebSocket disconnected. Attempting to reconnect in ${reconnectInterval / 1000}s...`,
    );
    // Clear the old socket reference
    socket = null;
    // Set a timer to attempt reconnection
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null; // Clear the timer before trying to connect
      connect();
    }, reconnectInterval);
  };

  socket.onerror = (error) => {
    console.error("WebSocket error:", error);
    // The onclose event will fire automatically after an error, triggering the reconnect logic.
    if (socket) {
      socket.close();
    }
  };
}

function disconnect() {
  // Clear any pending reconnect timers
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (socket) {
    socket.onclose = null; // Disable the reconnect logic
    socket.close();
    socket = null;
    console.log("WebSocket connection intentionally disconnected.");
  }
}

// Export a singleton service object
export const gitWebSocketService = {
  connect,
  disconnect,
};
