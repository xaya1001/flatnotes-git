import asyncio
from typing import Set, Dict

from logger import logger

# This class will manage all active client connections for SSE.
# It acts as a singleton that can be imported and used anywhere in the application.


class EventBroadcaster:
    def __init__(self):
        self.connections: Set[asyncio.Queue] = set()
        logger.info("EventBroadcaster initialized.")

    async def connect(self, queue: asyncio.Queue):
        """Adds a new client's queue to the set of active connections."""
        self.connections.add(queue)
        logger.info(f"New SSE client connected. Total clients: {len(self.connections)}")

    def disconnect(self, queue: asyncio.Queue):
        """Removes a client's queue when they disconnect."""
        self.connections.remove(queue)
        logger.info(f"SSE client disconnected. Total clients: {len(self.connections)}")

    async def broadcast(self, event_name: str, data: Dict):
        """Sends a message to all connected clients."""
        # We need to serialize the data to a string for SSE.
        import json

        message = json.dumps(data)

        logger.info(
            f"Broadcasting event '{event_name}' to {len(self.connections)} clients."
        )
        for queue in self.connections:
            await queue.put({"event": event_name, "data": message})


# Create a single, global instance of the broadcaster
broadcaster = EventBroadcaster()
