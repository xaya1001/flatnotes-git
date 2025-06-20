import os
import sys
from enum import Enum
from threading import Lock

import pygit2

from helpers import get_env
from logger import logger

logger.debug("Loading Git integration config...")


class PullStrategy(str, Enum):
    REBASE = "rebase"
    MERGE = "merge"


GIT_ENABLED: bool = get_env(
    "FLATNOTES_GIT_ENABLED", mandatory=False, default=False, cast_bool=True
)

GIT_REPO_PATH: str = get_env(
    "FLATNOTES_PATH",  # Using the same env var as the main notes path
    mandatory=True,  # If Git is enabled, this path must be set
)

GIT_REMOTE_NAME: str = get_env(
    "FLATNOTES_GIT_REMOTE_NAME", mandatory=False, default="origin"
)

GIT_DEFAULT_BRANCH: str = get_env(
    "FLATNOTES_GIT_DEFAULT_BRANCH", mandatory=False, default="main"
)

GIT_COMMIT_USER_NAME: str = get_env(
    "FLATNOTES_GIT_COMMIT_USER_NAME", mandatory=False, default="flatnotes-bot"
)

GIT_COMMIT_USER_EMAIL: str = get_env(
    "FLATNOTES_GIT_COMMIT_USER_EMAIL", mandatory=False, default="bot@flatnotes.local"
)

GIT_SSH_COMMAND: str = get_env(
    "FLATNOTES_GIT_SSH_COMMAND",
    mandatory=False,
    default=None,  # e.g., "ssh -i /path/to/key -o IdentitiesOnly=yes"
)

GIT_AUTO_SYNC_INTERVAL: int = get_env(
    "FLATNOTES_GIT_AUTO_SYNC_INTERVAL", mandatory=False, default=0, cast_int=True
)

GIT_AUTO_INIT: bool = get_env(
    "FLATNOTES_GIT_AUTO_INIT", mandatory=False, default=False, cast_bool=True
)

GIT_PULL_STRATEGY_STR: str = get_env(
    "FLATNOTES_GIT_PULL_STRATEGY", mandatory=False, default="rebase"
)
try:
    GIT_PULL_STRATEGY: PullStrategy = PullStrategy(GIT_PULL_STRATEGY_STR.lower())
except ValueError:
    logger.error(
        f"Invalid value '{GIT_PULL_STRATEGY_STR}' for FLATNOTES_GIT_PULL_STRATEGY. "
        "Must be one of 'rebase' or 'merge'. Defaulting to 'rebase'."
    )
    GIT_PULL_STRATEGY: PullStrategy = PullStrategy.REBASE


_auto_sync_paused_lock = Lock()
_is_auto_sync_paused: bool = False


def is_auto_sync_paused() -> bool:
    """Thread-safely check if auto-sync is paused."""
    with _auto_sync_paused_lock:
        return _is_auto_sync_paused


def pause_auto_sync():
    """Thread-safely pause the auto-sync feature."""
    with _auto_sync_paused_lock:
        global _is_auto_sync_paused
        _is_auto_sync_paused = True
    logger.info("Auto-sync has been paused via API.")


def resume_auto_sync():
    """Thread-safely resume the auto-sync feature."""
    with _auto_sync_paused_lock:
        global _is_auto_sync_paused
        _is_auto_sync_paused = False
    logger.info("Auto-sync has been resumed via API.")


if GIT_ENABLED:
    logger.info("Git integration is enabled.")
    logger.info(f"Using pull strategy: {GIT_PULL_STRATEGY.value}")
    if not os.path.isdir(GIT_REPO_PATH):
        logger.error(
            f"FLATNOTES_PATH (GIT_REPO_PATH) '{GIT_REPO_PATH}' is not a valid directory. Git integration functionality may fail."
        )
    elif not pygit2.discover_repository(GIT_REPO_PATH) and GIT_AUTO_INIT:
        logger.warning(
            f"No Git repository found in '{GIT_REPO_PATH}'. "
            f"FLATNOTES_GIT_AUTO_INIT is true, attempting to initialize a new repository."
        )
    if GIT_AUTO_SYNC_INTERVAL > 0:
        logger.info(
            f"Auto-sync is enabled with an interval of {GIT_AUTO_SYNC_INTERVAL} minutes."
        )
else:
    logger.info("Git integration is disabled.")
