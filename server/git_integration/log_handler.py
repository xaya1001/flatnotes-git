# server/git_integration/log_handler.py

import uuid
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Deque, List, Optional
from pydantic import BaseModel  # <--- 1. Import BaseModel

# Configuration
MAX_LOG_ENTRIES = 200


class LogLevel(str, Enum):
    """Enumeration for log levels."""

    INFO = "info"
    SUCCESS = "success"
    WARN = "warn"
    ERROR = "error"


# 2. Change from TypedDict to BaseModel
class LogEntry(BaseModel):
    """Structure for a single log entry, as a Pydantic model."""

    id: str
    timestamp: str
    level: LogLevel
    message: str
    details: Optional[str] = None


# In-memory log storage with a fixed size
_log_storage: Deque[LogEntry] = deque(maxlen=MAX_LOG_ENTRIES)
_lock = Lock()


def add_git_log(
    level: LogLevel,
    message: str,
    details: Optional[str] = None,
) -> None:
    """
    Adds a new entry to the in-memory Git log storage.

    Args:
        level: The severity level of the log entry.
        message: The main log message.
        details: Optional additional details, like stdout/stderr from commands.
    """
    with _lock:
        # 3. Create an instance of the model instead of a dictionary
        entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            details=details,
        )
        _log_storage.appendleft(entry)  # Prepend to keep newest logs at the start


def get_all_logs() -> List[LogEntry]:
    """
    Retrieves a copy of all current log entries.

    Returns:
        A list of all log entries, from newest to oldest.
    """
    with _lock:
        return list(_log_storage)
