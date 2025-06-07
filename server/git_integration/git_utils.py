import subprocess
import os
from typing import List, Tuple, Optional, Dict, Any

from .config import (
    GIT_REPO_PATH,
    GIT_SSH_COMMAND,
    GIT_COMMIT_USER_NAME,
    GIT_COMMIT_USER_EMAIL,
    GIT_REMOTE_NAME,
    GIT_DEFAULT_BRANCH,
    GIT_ENABLED
)
from .exceptions import GitCommandError
from logger import logger

def execute_git_command(
    command_args: List[str],
    check: bool = True,
    timeout: Optional[int] = 60, # Default timeout for git commands
    custom_env: Optional[dict] = None
) -> Tuple[str, str]:
    """
    Executes a Git command in the configured repository path.

    Args:
        command_args: A list of arguments for the git command (e.g., ["status", "--porcelain"]).
        check: If True, raises GitCommandError on non-zero exit code.
        timeout: Timeout in seconds for the command execution.
        custom_env: A dictionary of custom environment variables to set for the command.

    Returns:
        A tuple containing (stdout, stderr) of the command.

    Raises:
        GitCommandError: If 'check' is True and the command returns a non-zero exit code,
                         or if GIT_REPO_PATH is not a valid directory.
        FileNotFoundError: If git executable is not found.
    """
    if not GIT_ENABLED:
        message = "Git integration is disabled. Command not executed."
        logger.warning(message)
        # This function should ideally not be called if GIT_ENABLED is false from the API layer.
        # Raising an error might be more appropriate depending on how robust the calling code is.
        raise GitCommandError(message, command=['git'] + command_args, returncode=-1)

    if not GIT_REPO_PATH or not os.path.isdir(GIT_REPO_PATH):
        msg = f"Git repository path '{GIT_REPO_PATH}' is not configured or not a valid directory."
        logger.error(msg)
        raise GitCommandError(msg, returncode=-1, command=['git'] + command_args)

    # Prepare environment variables for the git command
    env = os.environ.copy()
    if GIT_SSH_COMMAND:
        env["GIT_SSH_COMMAND"] = GIT_SSH_COMMAND
        logger.debug(f"Using GIT_SSH_COMMAND: {GIT_SSH_COMMAND}")
    
    if GIT_COMMIT_USER_NAME:
        env["GIT_AUTHOR_NAME"] = GIT_COMMIT_USER_NAME
        env["GIT_COMMITTER_NAME"] = GIT_COMMIT_USER_NAME
    if GIT_COMMIT_USER_EMAIL:
        env["GIT_AUTHOR_EMAIL"] = GIT_COMMIT_USER_EMAIL
        env["GIT_COMMITTER_EMAIL"] = GIT_COMMIT_USER_EMAIL
        
    if custom_env:
        env.update(custom_env)

    full_command = ['git'] + command_args
    logger.info(f"Executing Git command: {' '.join(full_command)} in {GIT_REPO_PATH}")

    try:
        # Check if GIT_REPO_PATH is actually a git repository before running commands
        # (except for 'init' or 'clone' type commands, which are not used here directly)
        if command_args[0] not in ['version', 'init', 'clone']: # Add other commands that don't need a repo
            git_dir_check = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                cwd=GIT_REPO_PATH,
                capture_output=True,
                text=True,
                timeout=5, # Short timeout for this check
                env=env
            )
            if git_dir_check.returncode != 0 or git_dir_check.stdout.strip() != "true":
                msg = f"Path '{GIT_REPO_PATH}' is not a Git repository."
                logger.error(msg)
                raise GitCommandError(msg, stderr=git_dir_check.stderr.strip(), returncode=git_dir_check.returncode, command=full_command)

        process = subprocess.run(
            full_command,
            cwd=GIT_REPO_PATH,
            capture_output=True,
            text=True,
            check=False, 
            timeout=timeout,
            env=env
        )
    except FileNotFoundError:
        msg = "Git executable not found. Please ensure Git is installed and in PATH."
        logger.error(msg)
        raise 
    except subprocess.TimeoutExpired:
        msg = f"Git command {' '.join(full_command)} timed out after {timeout} seconds."
        logger.error(msg)
        raise GitCommandError(message=msg, command=full_command, returncode=-1, stderr="Timeout")

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()

    if stdout:
        logger.debug(f"Git command stdout:\n{stdout}")
    if stderr and process.returncode != 0: # Log stderr as warning only if there was an error
        logger.warning(f"Git command stderr:\n{stderr}")
    elif stderr: # Otherwise log as debug
        logger.debug(f"Git command stderr (info):\n{stderr}")


    if check and process.returncode != 0:
        error_message = f"Git command failed: {' '.join(full_command)}"
        logger.error(f"{error_message} - Return Code: {process.returncode}\nStderr: {stderr}")
        raise GitCommandError(
            message=error_message,
            stderr=stderr,
            returncode=process.returncode,
            command=full_command
        )

    return stdout, stderr

def get_status() -> Dict[str, Any]:
    """
    Gets the detailed status of the Git repository.
    Parses 'git status --porcelain=v1' for machine-readable output.

    Returns:
        A dictionary with 'files' (a list of file status details)
        and 'current_branch'.
        Example:
        {
            "files": [
                {"path": "file.txt", "index_status": "M", "work_tree_status": " ", "original_path": None},
                {"path": "new_file.txt", "index_status": "?", "work_tree_status": "?", "original_path": None},
                {"path": "renamed_new.txt", "index_status": "R", "work_tree_status": " ", "original_path": "renamed_old.txt"}
            ],
            "current_branch": "main"
        }
    """
    logger.info("Fetching detailed Git repository status.")
    # Using --porcelain=v1. For v2, add --porcelain=v2
    # v1 format: XY PATH or XY ORIG_PATH -> PATH
    stdout, _ = execute_git_command(["status", "--porcelain=v1"])
    
    files_status = []
    lines = stdout.splitlines()
    
    for line in lines:
        if not line:
            continue

        # Status codes are the first two characters
        index_status_char = line[0]
        work_tree_status_char = line[1]
        
        # Path part starts after the status codes and a space
        path_part = line[3:]
        
        original_path = None
        current_path = path_part

        # Check for rename/copy format: "XY ORIG_PATH -> NEW_PATH"
        # Note: Porcelain v1 status for rename (R) or copy (C) in index:
        # R  ORIG_PATH -> NEW_PATH  (NEW_PATH will be in path_part)
        # So, if index_status is R or C, we expect "ORIG_PATH -> NEW_PATH" if ORIG_PATH has spaces.
        # If no "->", then the path_part is just the (new) path.
        # A simple check: if "->" is present and index_status indicates rename/copy.
        if " -> " in path_part and (index_status_char == 'R' or index_status_char == 'C'):
            parts = path_part.split(" -> ", 1)
            original_path = parts[0]
            current_path = parts[1]
        
        files_status.append({
            "path": current_path,
            "index_status": index_status_char,
            "work_tree_status": work_tree_status_char,
            "original_path": original_path,
        })

    current_branch_name = get_current_branch() # Uses the existing helper

    return {
        "files": files_status,
        "current_branch": current_branch_name
    }


def add_all_changes() -> Tuple[str, str]:
    """
    Adds all changes (new, modified, deleted) in the working directory to the staging area.
    Uses 'git add -A'.
    """
    logger.info("Adding all changes to Git staging area.")
    stdout, stderr = execute_git_command(["add", "-A"])
    return stdout, stderr

def commit_changes(message: str) -> Tuple[str, str]:
    """
    Commits the staged changes with the given message.
    Uses 'git commit -m "message"'.
    Author and committer details are set via environment variables if configured.
    """
    if not message:
        raise ValueError("Commit message cannot be empty.")
    logger.info(f"Committing changes with message: '{message}'")
    
    # Check if there's anything to commit by looking at staged changes
    # `git diff --cached --quiet` exits with 0 if nothing staged, 1 if there are staged changes.
    # `git diff --cached --name-only` lists staged files.
    staged_files_stdout, _ = execute_git_command(["diff", "--cached", "--name-only"], check=False)
    if not staged_files_stdout:
        no_changes_msg = "No changes staged for commit."
        logger.info(no_changes_msg)
        # Returning a specific message rather than raising an error,
        # as this is not strictly an error but a state.
        return no_changes_msg, ""

    stdout, stderr = execute_git_command(["commit", "-m", message])
    return stdout, stderr

def pull_remote_changes(
    remote: Optional[str] = None, 
    branch: Optional[str] = None,
    rebase: bool = False,
    autostash: bool = True
) -> Tuple[str, str]:
    """
    Pulls changes from the specified remote and branch.
    Defaults to GIT_REMOTE_NAME and GIT_DEFAULT_BRANCH from config.
    Uses 'git pull <remote> <branch>'.
    """
    remote_to_use = remote or GIT_REMOTE_NAME
    branch_to_use = branch or GIT_DEFAULT_BRANCH
    command = ["pull", remote_to_use, branch_to_use]
    if rebase:
        command.append("--rebase")
    if autostash:
        command.append("--autostash")
        
    logger.info(f"Pulling changes from remote '{remote_to_use}', branch '{branch_to_use}' with options: rebase={rebase}, autostash={autostash}")
    stdout, stderr = execute_git_command(command, timeout=120) # Longer timeout for network ops
    return stdout, stderr

def push_local_changes(
    remote: Optional[str] = None, 
    branch: Optional[str] = None,
    force: bool = False
) -> Tuple[str, str]:
    """
    Pushes local commits to the specified remote and branch.
    Defaults to GIT_REMOTE_NAME and GIT_DEFAULT_BRANCH from config.
    Uses 'git push <remote> <branch>'.
    """
    remote_to_use = remote or GIT_REMOTE_NAME
    branch_to_use = branch or GIT_DEFAULT_BRANCH
    command = ["push", remote_to_use, branch_to_use]
    if force:
        command.append("--force") # Use with caution

    logger.info(f"Pushing local changes to remote '{remote_to_use}', branch '{branch_to_use}' with options: force={force}")
    stdout, stderr = execute_git_command(command, timeout=120) # Longer timeout for network ops
    return stdout, stderr

def get_commit_log(limit: int = 10, page: int = 1) -> List[Dict[str, str]]:
    """
    Retrieves the commit log from the repository.

    Args:
        limit: Number of log entries to retrieve.
        page: Page number for pagination (1-indexed).

    Returns:
        A list of dictionaries, where each dictionary represents a commit.
        Example: [{'hash': '...', 'author_name': '...', 'author_email': '...', 
                   'date': '...', 'message': '...'}]
    """
    if limit <= 0:
        limit = 10
    if page <= 0:
        page = 1
    
    skip_count = (page - 1) * limit

    # Using a custom format: %H (commit hash), %an (author name), %ae (author email), 
    # %ad (author date, ISO 8601 strict), %s (subject/message)
    # Using null byte as separator for robustness, then splitting.
    log_format = "%H%x00%an%x00%ae%x00%ad%x00%s"
    command = [
        "log",
        f"--pretty=format:{log_format}",
        f"--date=iso-strict", # Consistent date format
        f"-n {limit}",
    ]
    if skip_count > 0:
        command.append(f"--skip={skip_count}")

    logger.info(f"Fetching Git commit log (limit={limit}, page={page}).")
    
    try:
        stdout, _ = execute_git_command(command)
    except GitCommandError as e:
        # If the error is "does not have any commits yet", it's a common case for new repos
        if "does not have any commits yet" in e.stderr.lower() or \
           "bad default revision 'head'" in e.stderr.lower(): # Another common message for empty repo
            logger.info(f"Repository at {GIT_REPO_PATH} has no commits yet.")
            return []
        raise # Re-raise other GitCommandErrors

    if not stdout:
        return []

    log_entries = []
    raw_entries = stdout.strip().split('\n') # Each line is a full commit entry from the format

    for entry_line in raw_entries:
        if not entry_line:
            continue
        parts = entry_line.split('\x00') # Split by null byte
        if len(parts) == 5:
            log_entries.append({
                "hash": parts[0],
                "author_name": parts[1],
                "author_email": parts[2],
                "date": parts[3],
                "message": parts[4],
            })
        else:
            logger.warning(f"Could not parse log entry: {entry_line}. Expected 5 parts, got {len(parts)}")
            
    return log_entries

def get_current_branch() -> Optional[str]:
    """
    Gets the current active branch name.
    Returns None if not on a branch (e.g., detached HEAD).
    """
    logger.info("Fetching current Git branch.")
    try:
        # 'git symbolic-ref --short HEAD' is good for local branches
        # 'git branch --show-current' is simpler but newer (Git 2.22+)
        # 'git rev-parse --abbrev-ref HEAD' is a robust option
        stdout, stderr = execute_git_command(["rev-parse", "--abbrev-ref", "HEAD"], check=True)
        if stdout == "HEAD": # Detached HEAD state
            return None 
        return stdout
    except GitCommandError as e:
        logger.error(f"Could not determine current branch: {e.stderr}")
        # This can happen in an empty repo before the first commit
        if "unknown revision or path not in the working tree" in e.stderr.lower() or \
           "bad default revision 'head'" in e.stderr.lower():
            logger.info(f"Repository at {GIT_REPO_PATH} seems to be empty or without a HEAD.")
            return None # Or a default like 'main' if appropriate, but None is more accurate
        return None # Or re-raise, but returning None might be safer for UI

def get_remote_url(remote_name: Optional[str] = None) -> Optional[str]:
    """
    Gets the URL of the specified remote.
    Defaults to GIT_REMOTE_NAME from config.
    """
    remote_to_use = remote_name or GIT_REMOTE_NAME
    logger.info(f"Fetching URL for remote '{remote_to_use}'.")
    try:
        stdout, _ = execute_git_command(["remote", "get-url", remote_to_use], check=True)
        return stdout
    except GitCommandError as e:
        logger.warning(f"Could not get URL for remote '{remote_to_use}': {e.stderr}")
        return None

# --- End of git_utils.py ---