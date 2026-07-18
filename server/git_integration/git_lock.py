import asyncio
import threading
from contextlib import asynccontextmanager

git_operation_lock = threading.Lock()


@asynccontextmanager
async def locked_git_operation():
    """Serializes Git writes without blocking the event loop while waiting."""
    await asyncio.to_thread(git_operation_lock.acquire)
    try:
        yield
    finally:
        git_operation_lock.release()
