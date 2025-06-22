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
      `WebSocket disconnected. Attempting to reconnect in ${reconnectInterval / 1000}s...`,
    );
    socket = null;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, reconnectInterval);
  };

  socket.onerror = (error) => {
    console.error("WebSocket error:", error);
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
