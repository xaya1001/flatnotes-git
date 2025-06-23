# server/git_integration/websockets.py
from typing import List

from fastapi import WebSocket, WebSocketDisconnect

from logger import logger


class ConnectionManager:
    """Manages all active WebSocket connections and handles broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accepts and stores a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected: {websocket.client.host}")

    def disconnect(self, websocket: WebSocket):
        """Removes a disconnected WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected: {websocket.client.host}")

    async def broadcast_status_update(self):
        """Broadcasts a status update trigger signal to all connected clients."""
        # We only send a lightweight trigger signal, not the full state.
        # The client, upon receiving this, will actively fetch the latest state,
        # perfectly reusing the existing logic.
        message = {"type": "status_update"}
        logger.info(
            f"Broadcasting status update to {len(self.active_connections)} clients."
        )
        # Create a copy to prevent modification during iteration
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                # Handle cases where the client has disconnected without a clean close
                self.disconnect(connection)
            except Exception as e:
                logger.error(
                    f"Error sending to WebSocket client {connection.client.host}: {e}"
                )
                self.disconnect(connection)


# Create a global singleton instance for application-wide use
connection_manager = ConnectionManager()
