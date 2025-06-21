# server/git_integration/git_logger.py

import json
import os
import uuid
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Deque, List, Optional

from pydantic import BaseModel, ValidationError

from logger import logger

from .git_config import GIT_REPO_PATH

# Configuration
MAX_LOG_ENTRIES = 200
LOG_FILE_PATH = os.path.join(GIT_REPO_PATH, ".flatnotes", "git_activity.log")


class LogLevel(str, Enum):
    """Enumeration for log levels."""

    INFO = "info"
    SUCCESS = "success"
    WARN = "warn"
    ERROR = "error"


class LogEntry(BaseModel):
    """Structure for a single log entry, as a Pydantic model."""

    id: str
    timestamp: str
    level: LogLevel
    message: str
    details: Optional[Any] = None


# In-memory log storage with a fixed size
_log_storage: Deque[LogEntry] = deque(maxlen=MAX_LOG_ENTRIES)
_lock = Lock()


def _ensure_log_dir_exists():
    """Ensures the directory for the log file exists."""
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not create log directory at {log_dir}: {e}")


def _persist_log_entry(entry: LogEntry):
    """Appends a single log entry to the persistent log file."""
    try:
        # Using model_dump_json for direct, reliable JSON conversion
        with open(LOG_FILE_PATH, "a") as f:
            f.write(entry.model_dump_json() + "\n")
    except IOError as e:
        logger.error(f"Failed to write to persistent git log file: {e}")


def add_git_log(
    level: LogLevel,
    message: str,
    details: Optional[Any] = None,
    persist: bool = True,
) -> None:
    """
    Adds a new entry to the in-memory Git log storage and optionally persists it.

    Args:
        level: The severity level of the log entry.
        message: The main log message.
        details: Optional additional structured data about the operation.
        persist: If True, the log will be saved to the persistent log file.
                 Set to False for transient logs like "refresh".
    """
    with _lock:
        entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            details=details,
        )
        _log_storage.appendleft(entry)

        if persist:
            _persist_log_entry(entry)


def get_all_logs() -> List[LogEntry]:
    """
    Retrieves a copy of all current log entries.

    Returns:
        A list of all log entries, from newest to oldest.
    """
    with _lock:
        return list(_log_storage)


def clear_all_logs():
    """Clears both the in-memory log cache and the persistent log file."""
    with _lock:
        _log_storage.clear()
        if os.path.exists(LOG_FILE_PATH):
            try:
                os.remove(LOG_FILE_PATH)
                logger.info(f"Persistent log file deleted: {LOG_FILE_PATH}")
            except OSError as e:
                logger.error(f"Failed to delete persistent log file: {e}")
                # We raise the error so the API can report a failure
                raise e


def _load_logs_from_disk():
    """Loads log entries from the persistent file into the in-memory deque."""
    _ensure_log_dir_exists()
    if not os.path.exists(LOG_FILE_PATH):
        return

    loaded_entries = []
    with _lock:
        try:
            with open(LOG_FILE_PATH, "r") as f:
                # Read all lines and take the last MAX_LOG_ENTRIES
                all_lines = f.readlines()
                relevant_lines = all_lines[-MAX_LOG_ENTRIES:]
                for line in relevant_lines:
                    try:
                        data = json.loads(line)
                        loaded_entries.append(LogEntry(**data))
                    except (json.JSONDecodeError, ValidationError) as e:
                        logger.warning(
                            f"Skipping corrupt log line: {line.strip()}. Error: {e}"
                        )
            # Sort by timestamp descending to ensure newest are first
            loaded_entries.sort(key=lambda x: x.timestamp, reverse=True)
            _log_storage.clear()
            _log_storage.extend(loaded_entries)
            logger.info(f"Loaded {len(_log_storage)} git activity logs from disk.")
        except IOError as e:
            logger.error(f"Failed to read from persistent git log file: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading git logs: {e}")


# Load logs on module initialization
_load_logs_from_disk()
