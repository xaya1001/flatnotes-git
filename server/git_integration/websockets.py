# server/git_integration/websockets.py
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)

from auth.base import BaseAuth
from logger import logger

# Create a new, dedicated router for WebSocket endpoints
ws_router = APIRouter()


async def get_websocket_token(websocket: WebSocket):
    """
    A dependency function to authenticate WebSocket connections using a cookie.
    If authentication fails, it raises a WebSocketException, which cleanly
    terminates the connection and prevents the endpoint from running.
    """
    auth_service: Optional[BaseAuth] = getattr(websocket.app.state, "auth", None)

    if not auth_service:
        # If auth is disabled, allow the connection to proceed.
        return

    token = websocket.cookies.get("token")
    if token is None:
        logger.warning(
            f"WebSocket connection rejected for {websocket.client.host}: Missing token cookie."
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Missing token"
        )

    try:
        # Use the now-public validation logic from the existing auth module
        auth_service.validate_token(token)
        logger.debug(
            f"WebSocket client authenticated successfully: {websocket.client.host}"
        )
    except Exception:
        logger.warning(
            f"WebSocket authentication failed for client: {websocket.client.host}"
        )
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
        )


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
        message = {"type": "status_update"}
        logger.info(
            f"Broadcasting status update to {len(self.active_connections)} clients."
        )
        # Create a copy to prevent modification during iteration
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                self.disconnect(connection)
            except Exception as e:
                logger.error(
                    f"Error sending to WebSocket client {connection.client.host}: {e}"
                )
                self.disconnect(connection)


# Create a global singleton instance for application-wide use
connection_manager = ConnectionManager()


@ws_router.websocket("/ws/status", dependencies=[Depends(get_websocket_token)])
async def websocket_endpoint(websocket: WebSocket):
    """
    The authenticated WebSocket endpoint. The dependency ensures that this
    code is only run for valid, authenticated clients.
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by waiting for messages (or pings).
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
