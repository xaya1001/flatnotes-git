import subprocess
import os
from typing import List, Tuple, Optional, Dict, Any

from .config import (
    GIT_REPO_PATH,
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
    timeout: Optional[int] = 60,
    env_override: Optional[dict] = None
) -> Tuple[str, str]:
    """
    Executes a Git command, relying on the pre-configured environment
    set up by entrypoint.sh. 
    """
    if not GIT_ENABLED:
        raise GitCommandError("Git integration is disabled.", command=['git'] + command_args, returncode=-1)

    if not GIT_REPO_PATH or not os.path.isdir(GIT_REPO_PATH):
        raise GitCommandError(f"Git repository path '{GIT_REPO_PATH}' is not valid.", returncode=-1, command=['git'] + command_args)

    git_command_prefix = ['git', '-c', 'core.quotePath=false']
    full_command = git_command_prefix + command_args
    
    logger.info(f"Executing: {' '.join(full_command)}")

    effective_env = None
    if env_override:
        effective_env = os.environ.copy()
        effective_env.update(env_override)

    try:
        process = subprocess.run(
            full_command,
            cwd=GIT_REPO_PATH,
            capture_output=True,
            encoding='utf-8',
            errors='strict',
            check=False, 
            timeout=timeout,
            env=effective_env 
        )
    except FileNotFoundError:
        raise GitCommandError("Git executable not found. Please ensure Git is installed.", command=full_command)
    except subprocess.TimeoutExpired:
        raise GitCommandError(f"Git command timed out after {timeout} seconds.", command=full_command)

    stdout, stderr = process.stdout.strip(), process.stderr.strip()
    if stdout: logger.debug(f"stdout:\n{stdout}")
    if stderr: logger.warning(f"stderr:\n{stderr}")

    if check and process.returncode != 0:
        raise GitCommandError(
            f"Git command failed: {' '.join(full_command)}",
            stderr=stderr, returncode=process.returncode, command=full_command
        )
    return stdout, stderr

def get_status() -> Dict[str, Any]:
    """
    Gets the detailed status of the Git repository by diffing the index
    and the working tree separately for maximum reliability.
    """
    all_files = {}

    staged_stdout, _ = execute_git_command(['diff', '--name-status', '--cached', 'HEAD'])
    for line in staged_stdout.splitlines():
        if not line: continue
        parts = line.split('\t')
        status, filepath = parts[0][0], parts[-1]
        original_path = parts[1] if len(parts) == 3 else None
        all_files[filepath] = {'path': filepath, 'index_status': status, 'work_tree_status': ' ', 'original_path': original_path}

    unstaged_stdout, _ = execute_git_command(['diff', '--name-status'])
    for line in unstaged_stdout.splitlines():
        if not line: continue
        parts = line.split('\t')
        status, filepath = parts[0][0], parts[-1]
        original_path = parts[1] if len(parts) == 3 else None
        if filepath in all_files:
            all_files[filepath]['work_tree_status'] = status
        else:
            all_files[filepath] = {'path': filepath, 'index_status': ' ', 'work_tree_status': status, 'original_path': original_path}
            
    untracked_stdout, _ = execute_git_command(['ls-files', '--others', '--exclude-standard'])
    for filepath in untracked_stdout.splitlines():
        if not filepath: continue
        all_files[filepath] = {'path': filepath, 'index_status': '?', 'work_tree_status': '?', 'original_path': None}

    return {"files": list(all_files.values()), "current_branch": get_current_branch()}

def add_file(filepath: str) -> Tuple[str, str]:
    return execute_git_command(["add", "--", filepath])

def add_all_changes() -> Tuple[str, str]:
    return execute_git_command(["add", "-A"])

def unstage_file(filepath: str) -> Tuple[str, str]:
    return execute_git_command(["restore", "--staged", "--", filepath])

def discard_file_changes(filepath: str) -> Tuple[str, str]:
    stdout, _ = execute_git_command(['ls-files', '--', filepath])
    if not stdout:
        return execute_git_command(["clean", "-fd", "--", filepath])
    else:
        return execute_git_command(["restore", "--", filepath])

def discard_all_changes() -> Tuple[str, str]:
    stdout_restore, stderr_restore = execute_git_command(["restore", "--", "."])
    stdout_clean, stderr_clean = execute_git_command(["clean", "-fd"])
    stdout = f"Restore output:\n{stdout_restore}\n\nClean output:\n{stdout_clean}"
    stderr = f"Restore stderr:\n{stderr_restore}\n\nClean stderr:\n{stderr_clean}"
    return stdout, stderr

def commit_changes(message: str) -> Tuple[str, str]:
    if not message: raise ValueError("Commit message cannot be empty.")
    staged_files_stdout, _ = execute_git_command(["diff", "--cached", "--name-only"], check=False)
    if not staged_files_stdout:
        return "No changes staged for commit.", ""
    commit_env = {}
    if GIT_COMMIT_USER_NAME:
        commit_env["GIT_AUTHOR_NAME"] = GIT_COMMIT_USER_NAME
        commit_env["GIT_COMMITTER_NAME"] = GIT_COMMIT_USER_NAME
    if GIT_COMMIT_USER_EMAIL:
        commit_env["GIT_AUTHOR_EMAIL"] = GIT_COMMIT_USER_EMAIL
        commit_env["GIT_COMMITTER_EMAIL"] = GIT_COMMIT_USER_EMAIL
    return execute_git_command(["commit", "-m", message], env_override=commit_env)

def pull_remote_changes(remote: Optional[str] = None, branch: Optional[str] = None, rebase: bool = False, autostash: bool = True) -> Tuple[str, str]:
    remote_to_use, branch_to_use = remote or GIT_REMOTE_NAME, branch or GIT_DEFAULT_BRANCH
    command = ["pull", remote_to_use, branch_to_use]
    if rebase: command.append("--rebase")
    if autostash: command.append("--autostash")
    logger.info(f"Pulling changes from remote '{remote_to_use}', branch '{branch_to_use}'")
    
    try:
        # For pull/push, we set check=False and handle errors manually
        # because many "errors" are just states we need to report to the user.
        stdout, stderr = execute_git_command(command, check=False, timeout=120)

        if "fatal: Authentication failed" in stderr:
            # Re-raise as a specific, catchable error
            raise GitCommandError("Authentication failed. Please check your SSH key setup.", stderr=stderr)
        
        if "Merge conflict" in stderr or "Automatic merge failed" in stderr:
            # Abort the merge to return to a clean state
            logger.warning("Merge conflict detected during pull. Aborting merge...")
            execute_git_command(["merge", "--abort"], check=False)
            raise GitCommandError("Merge conflict detected. Please resolve conflicts manually.", stderr=stderr)

        return stdout, stderr
        
    except GitCommandError as e:
        # Re-raise any already-caught GitCommandErrors
        raise
    except Exception as e:
        # Catch any other unexpected exceptions
        logger.error(f"An unexpected error occurred during pull: {e}", exc_info=True)
        raise

def push_local_changes(remote: Optional[str] = None, branch: Optional[str] = None, force: bool = False) -> Tuple[str, str]:
    remote_to_use, branch_to_use = remote or GIT_REMOTE_NAME, branch or GIT_DEFAULT_BRANCH
    command = ["push", remote_to_use, branch_to_use]
    if force: command.append("--force")
    logger.info(f"Pushing local changes to remote '{remote_to_use}', branch '{branch_to_use}'")

    try:
        stdout, stderr = execute_git_command(command, check=False, timeout=120)
        
        if "failed to push some refs" in stderr:
            logger.warning(f"Push rejected. Details: {stderr}")
            # This often means the remote has work you don't have locally.
            # A common suggestion is to pull first.
            raise GitCommandError("Push rejected. Tip: Try pulling remote changes first.", stderr=stderr)
            
        return stdout, stderr
    except GitCommandError as e:
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during push: {e}", exc_info=True)
        raise

def get_commit_log(limit: int = 10, page: int = 1) -> List[Dict[str, str]]:
    if limit <= 0: limit = 10
    if page <= 0: page = 1
    skip_count = (page - 1) * limit
    log_format = "%H%x00%an%x00%ae%x00%ad%x00%s"
    command = ["log", f"--pretty=format:{log_format}", f"--date=iso-strict", f"-n {limit}"]
    if skip_count > 0: command.append(f"--skip={skip_count}")
    try:
        stdout, _ = execute_git_command(command)
    except GitCommandError as e:
        if "does not have any commits yet" in e.stderr.lower(): return []
        raise
    if not stdout: return []
    log_entries = []
    for entry_line in stdout.strip().split('\n'):
        if not entry_line: continue
        parts = entry_line.split('\x00')
        if len(parts) == 5:
            log_entries.append({"hash": parts[0], "author_name": parts[1], "author_email": parts[2], "date": parts[3], "message": parts[4]})
    return log_entries

def get_current_branch() -> Optional[str]:
    try:
        stdout, _ = execute_git_command(["rev-parse", "--abbrev-ref", "HEAD"], check=True)
        return None if stdout == "HEAD" else stdout
    except GitCommandError:
        return None

def get_remote_url(remote_name: Optional[str] = None) -> Optional[str]:
    try:
        return execute_git_command(["remote", "get-url", remote_name or GIT_REMOTE_NAME], check=True)[0]
    except GitCommandError:
        return None

def get_status_summary() -> Dict[str, Any]:
    """Gets a lightweight summary of the Git repository status."""
    branch = get_current_branch()
    # Use ls-files to count all changes (staged, unstaged, untracked)
    staged_stdout, _ = execute_git_command(['diff', '--name-only', '--cached', 'HEAD'])
    unstaged_stdout, _ = execute_git_command(['diff', '--name-only'])
    untracked_stdout, _ = execute_git_command(['ls-files', '--others', '--exclude-standard'])
    
    # Use a set to count unique changed files
    changed_files = set(staged_stdout.splitlines())
    changed_files.update(unstaged_stdout.splitlines())
    changed_files.update(untracked_stdout.splitlines())
    
    return {"current_branch": branch, "files_changed_count": len(changed_files)}