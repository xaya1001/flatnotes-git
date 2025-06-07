import os
from helpers import get_env
from logger import logger

logger.debug("Loading Git integration config...")

GIT_ENABLED: bool = get_env(
    "FLATNOTES_GIT_ENABLED", 
    mandatory=False, 
    default=False, 
    cast_bool=True
)

GIT_REPO_PATH: str = get_env(
    "FLATNOTES_PATH", # Using the same env var as the main notes path
    mandatory=True # If Git is enabled, this path must be set
) 

GIT_REMOTE_NAME: str = get_env(
    "FLATNOTES_GIT_REMOTE_NAME",
    mandatory=False,
    default="origin"
)

GIT_DEFAULT_BRANCH: str = get_env(
    "FLATNOTES_GIT_DEFAULT_BRANCH",
    mandatory=False,
    default="main"
)

GIT_COMMIT_USER_NAME: str = get_env(
    "FLATNOTES_GIT_COMMIT_USER_NAME",
    mandatory=False,
    default=None # Allow Git to use its system/repo config
)

GIT_COMMIT_USER_EMAIL: str = get_env(
    "FLATNOTES_GIT_COMMIT_USER_EMAIL",
    mandatory=False,
    default=None # Allow Git to use its system/repo config
)

GIT_SSH_COMMAND: str = get_env(
    "FLATNOTES_GIT_SSH_COMMAND",
    mandatory=False,
    default=None # e.g., "ssh -i /path/to/key -o IdentitiesOnly=yes"
)

if GIT_ENABLED:
    logger.info("Git integration is enabled.")
    if not os.path.isdir(GIT_REPO_PATH):
        logger.error(f"FLATNOTES_PATH (GIT_REPO_PATH) '{GIT_REPO_PATH}' is not a valid directory. Git integration functionality may fail.")
else:
    logger.info("Git integration is disabled.")