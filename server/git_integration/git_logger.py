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

# --- Special ID for the auto-fetch task ---
AUTO_FETCH_LOG_ID = "auto-fetch-task"


def add_git_log(
    level: LogLevel,
    message: str,
    details: Optional[Any] = None,
    persist: bool = True,
    log_id: Optional[str] = None,
) -> None:
    """
    Adds or updates an entry in the Git log storage.
    If a log_id is provided and exists, it updates it. Otherwise, it adds a new entry.
    """
    with _lock:
        # If a specific log_id is given, try to find and update it.
        if log_id:
            # Find the entry to update
            if existing_entry := next(
                (entry for entry in _log_storage if entry.id == log_id), None
            ):
                # Update existing entry in-place
                existing_entry.timestamp = datetime.now(timezone.utc).isoformat()
                existing_entry.level = level
                existing_entry.message = message
                existing_entry.details = details

                # If this update should be persisted (e.g., a failure), persist it.
                if persist:
                    _persist_log_entry(existing_entry)
                return

        # If no update occurred, create a new entry.
        entry_id = log_id or str(uuid.uuid4())
        new_entry = LogEntry(
            id=entry_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            details=details,
        )
        _log_storage.appendleft(new_entry)

        if persist:
            _persist_log_entry(new_entry)


def get_all_logs() -> List[LogEntry]:
    """Retrieves a copy of all current log entries."""
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
                raise e


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
    # This function is now simpler as it just writes. The decision to call it is made in add_git_log.
    _ensure_log_dir_exists()
    try:
        with open(LOG_FILE_PATH, "a") as f:
            f.write(entry.model_dump_json() + "\n")
    except IOError as e:
        logger.error(f"Failed to write to persistent git log file: {e}")


def _load_logs_from_disk():
    """Loads log entries from the persistent file into the in-memory deque."""
    _ensure_log_dir_exists()
    if not os.path.exists(LOG_FILE_PATH):
        return

    loaded_entries = []
    with _lock:
        try:
            with open(LOG_FILE_PATH, "r") as f:
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
