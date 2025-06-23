# server/git_integration/git_config.py

from enum import Enum

from logger import logger

# This file acts as a centralized module for Git-related configuration constants.
# It is populated once at application startup by the GlobalConfig object.
# It does NOT read environment variables itself.


class PullStrategy(str, Enum):
    REBASE = "rebase"
    MERGE = "merge"


# --- Configuration Constants ---
# These are initialized with placeholder/default values and will be
# overwritten by the _initialize_git_config function at startup.

GIT_ENABLED: bool = False
GIT_REPO_PATH: str = ""
GIT_REMOTE_NAME: str = "origin"
GIT_DEFAULT_BRANCH: str = "main"
GIT_COMMIT_USER_NAME: str = "flatnotes-bot"
GIT_COMMIT_USER_EMAIL: str = "bot@flatnotes.local"
GIT_SSH_COMMAND: str = None
GIT_AUTO_INIT: bool = False
GIT_PULL_STRATEGY: PullStrategy = PullStrategy.REBASE

# --- Sync Strategy Constants ---
GIT_WEBHOOK_SECRET: str = None
GIT_WEBHOOK_ACTIVE: bool = False  # NEW: Flag to indicate if webhook is truly active
GIT_AUTO_FETCH_INTERVAL: int = 0


def initialize_git_config(global_config):
    """
    Populates the git configuration constants from the global_config object.
    This function should be called only once at application startup from main.py.
    """
    # Use 'global' to modify the module-level variables
    global GIT_ENABLED, GIT_REPO_PATH, GIT_REMOTE_NAME, GIT_DEFAULT_BRANCH
    global GIT_COMMIT_USER_NAME, GIT_COMMIT_USER_EMAIL, GIT_SSH_COMMAND
    global GIT_AUTO_INIT, GIT_PULL_STRATEGY, GIT_WEBHOOK_SECRET
    global GIT_AUTO_FETCH_INTERVAL, GIT_WEBHOOK_ACTIVE

    GIT_ENABLED = global_config.flatnotes_git_enabled
    if not GIT_ENABLED:
        return

    # These are only relevant if Git is enabled
    GIT_REPO_PATH = global_config.flatnotes_path
    GIT_REMOTE_NAME = global_config.flatnotes_git_remote_name
    GIT_DEFAULT_BRANCH = global_config.flatnotes_git_default_branch
    GIT_COMMIT_USER_NAME = global_config.flatnotes_git_commit_user_name
    GIT_COMMIT_USER_EMAIL = global_config.flatnotes_git_commit_user_email
    GIT_SSH_COMMAND = global_config.flatnotes_git_ssh_command
    GIT_AUTO_INIT = global_config.flatnotes_git_auto_init

    # Sync Strategy
    GIT_WEBHOOK_SECRET = global_config.flatnotes_git_webhook_secret
    GIT_WEBHOOK_ACTIVE = global_config.flatnotes_git_webhook_active
    GIT_AUTO_FETCH_INTERVAL = global_config.flatnotes_git_auto_fetch_interval

    try:
        GIT_PULL_STRATEGY = PullStrategy(
            global_config.flatnotes_git_pull_strategy.lower()
        )
    except ValueError:
        logger.error(
            f"Invalid value '{global_config.flatnotes_git_pull_strategy}' for pull strategy. "
            "Defaulting to 'rebase'."
        )
        GIT_PULL_STRATEGY = PullStrategy.REBASE
