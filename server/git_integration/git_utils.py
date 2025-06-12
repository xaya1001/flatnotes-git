# server/git_integration/git_utils.py
import os
from typing import Any, Dict, List, Optional, Tuple

import git
from git import Actor
from git import GitCommandError as GitPythonError

from logger import logger
from datetime import datetime

from .config import (
    GIT_COMMIT_USER_EMAIL,
    GIT_COMMIT_USER_NAME,
    GIT_DEFAULT_BRANCH,
    GIT_ENABLED,
    GIT_REMOTE_NAME,
    GIT_REPO_PATH,
)

# --- GitPython Repo Initialization ---
repo: Optional[git.Repo] = None

if GIT_ENABLED:
    try:
        if not os.path.isdir(GIT_REPO_PATH):
            raise git.exc.InvalidGitRepositoryError(
                f"Path '{GIT_REPO_PATH}' is not a valid directory."
            )

        repo = git.Repo(GIT_REPO_PATH)

        ssh_cmd = os.environ.get("GIT_SSH_COMMAND")
        if ssh_cmd:
            repo.git.update_environment(GIT_SSH_COMMAND=ssh_cmd)

        logger.info(f"GitPython initialized for repository at: {GIT_REPO_PATH}")

    except git.exc.InvalidGitRepositoryError:
        logger.error(
            f"'{GIT_REPO_PATH}' is not a valid Git repository. Git features will be non-functional."
        )
    except git.exc.NoSuchPathError:
        logger.error(
            f"The path '{GIT_REPO_PATH}' does not exist. Git features will be non-functional."
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while initializing GitPython: {e}",
            exc_info=True,
        )


def _check_repo():
    """Helper to ensure the repo object is valid before use."""
    if not repo:
        raise GitPythonError(
            "git init", 1, "Git repository is not available or invalid.", ""
        )


def _get_remote(remote_name_arg: Optional[str] = None) -> git.Remote:
    """Safely gets a remote, raising a specific error if not found."""
    _check_repo()
    if not repo.remotes:
        raise GitPythonError(
            "git remote",
            1,
            "No remotes configured in the repository. Please add a remote.",
            "",
        )

    remote_to_use_name = remote_name_arg or GIT_REMOTE_NAME
    try:
        return repo.remotes[remote_to_use_name]
    except IndexError:
        raise GitPythonError(
            "git remote",
            1,
            f"Remote '{remote_to_use_name}' not found. Available remotes: {[r.name for r in repo.remotes]}",
            "",
        )


# --- Rewritten Functions ---


def get_status() -> Dict[str, Any]:
    _check_repo()
    all_files = {}

    for diff in repo.index.diff("HEAD"):
        status = diff.change_type
        filepath = diff.a_path
        original_path = diff.rename_from if diff.renamed else None
        all_files[filepath] = {
            "path": filepath,
            "index_status": status,
            "work_tree_status": " ",
            "original_path": original_path,
        }

    for diff in repo.index.diff(None):
        status = diff.change_type
        filepath = diff.a_path
        original_path = diff.rename_from if diff.renamed else None
        if filepath in all_files:
            all_files[filepath]["work_tree_status"] = status
        else:
            all_files[filepath] = {
                "path": filepath,
                "index_status": " ",
                "work_tree_status": status,
                "original_path": original_path,
            }

    for filepath in repo.untracked_files:
        all_files[filepath] = {
            "path": filepath,
            "index_status": "?",
            "work_tree_status": "?",
            "original_path": None,
        }

    return {"files": list(all_files.values()), "current_branch": get_current_branch()}


def add_file(filepath: str) -> Tuple[str, str]:
    _check_repo()
    repo.index.add([filepath])
    return f"File '{filepath}' added to index.", ""


def add_all_changes() -> Tuple[str, str]:
    _check_repo()
    repo.git.add(A=True)
    return "All changes added to index.", ""


def unstage_file(filepath: str) -> Tuple[str, str]:
    _check_repo()
    repo.index.reset("HEAD", paths=[filepath])
    return f"File '{filepath}' removed from index.", ""


def unstage_all_files() -> Tuple[str, str]:
    _check_repo()
    repo.index.reset("HEAD")
    return "All files removed from index.", ""


def discard_file_changes(filepath: str) -> Tuple[str, str]:
    _check_repo()
    if filepath in repo.untracked_files:
        full_path = os.path.join(GIT_REPO_PATH, filepath)
        os.remove(full_path)
        return f"Untracked file '{filepath}' deleted.", ""
    else:
        repo.git.checkout("--", filepath)
        return f"Changes to '{filepath}' discarded.", ""


def discard_all_changes() -> Tuple[str, str]:
    _check_repo()
    repo.git.restore("--", ".")
    repo.git.clean("-fd")
    return "All unstaged changes and untracked files have been discarded.", ""


def _format_commit_message(template: str) -> str:
    """Replaces placeholders in a commit message template."""
    _check_repo()

    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    template = template.replace("{{date}}", current_date)

    if "{{numFiles}}" in template:
        staged_files_count = len(repo.index.diff("HEAD"))
        template = template.replace("{{numFiles}}", str(staged_files_count))

    return template


def commit_changes(message: str) -> Tuple[str, str]:
    _check_repo()
    if not message:
        raise ValueError("Commit message cannot be empty.")

    formatted_message = _format_commit_message(message)

    if not repo.index.diff("HEAD"):
        return "No changes staged for commit.", ""

    author = (
        Actor(GIT_COMMIT_USER_NAME, GIT_COMMIT_USER_EMAIL)
        if GIT_COMMIT_USER_NAME and GIT_COMMIT_USER_EMAIL
        else None
    )
    commit_obj = repo.index.commit(formatted_message, author=author, committer=author)
    return f"Committed as {commit_obj.hexsha}", ""


def pull_remote_changes(
    remote: Optional[str] = None, branch: Optional[str] = None, **kwargs
) -> Tuple[str, str]:
    remote_to_use = _get_remote(remote)
    try:
        fetch_info_list = remote_to_use.pull(refspec=branch or GIT_DEFAULT_BRANCH)
        messages = [info.note for info in fetch_info_list if info.note]
        return "\n".join(messages) or "Pull successful.", ""
    except GitPythonError as e:
        if "Merge conflict" in e.stderr or "Automatic merge failed" in e.stderr:
            logger.warning("Merge conflict detected during pull. Aborting merge...")
            repo.git.merge("--abort")
            raise GitPythonError(
                e.command,
                e.status,
                "Merge conflict detected. Please resolve conflicts manually.",
                e.stderr,
            ) from e
        raise


def push_local_changes(
    remote: Optional[str] = None, branch: Optional[str] = None, **kwargs
) -> Tuple[str, str]:
    remote_to_use = _get_remote(remote)
    push_info_list = remote_to_use.push(refspec=branch or GIT_DEFAULT_BRANCH)
    for info in push_info_list:
        if info.flags & (info.ERROR | info.REJECTED):
            raise GitPythonError(
                f"push {remote_to_use.name}", info.flags, info.summary, info.summary
            )
    return "Push successful.", ""


def get_commit_log(limit: int = 10, page: int = 1) -> List[Dict[str, Any]]:
    _check_repo()
    skip_count = (page - 1) * limit
    try:
        commits = list(repo.iter_commits(max_count=limit, skip=skip_count))
    except git.exc.GitCommandError as e:
        if "does not have any commits yet" in e.stderr.lower():
            return []
        raise

    log_entries = []
    for commit in commits:
        log_entries.append(
            {
                "hash": commit.hexsha,
                "author_name": commit.author.name,
                "author_email": commit.author.email,
                "date": commit.authored_datetime.isoformat(),
                "message": commit.message.strip(),
            }
        )
    return log_entries


def get_current_branch() -> Optional[str]:
    _check_repo()
    try:
        return repo.active_branch.name
    except TypeError:
        return "HEAD (Detached)"


def get_remote_url(remote_name: Optional[str] = None) -> Optional[str]:
    try:
        remote = _get_remote(remote_name)
        return remote.url
    except GitPythonError:
        return None


def get_status_summary() -> Dict[str, Any]:
    _check_repo()
    changed_files_count = (
        len(repo.index.diff("HEAD"))
        + len(repo.index.diff(None))
        + len(repo.untracked_files)
    )
    return {
        "current_branch": get_current_branch(),
        "files_changed_count": changed_files_count,
    }


def sync_workspace(commit_message: str) -> Tuple[str, str]:
    _check_repo()
    logger.info("Starting workspace sync...")

    add_stdout, add_stderr = add_all_changes()
    logger.info("Sync: All changes added.")

    if not repo.index.diff("HEAD"):
        logger.info("Sync: No changes to commit.")
        commit_stdout = "No changes to commit."
    else:
        formatted_message = _format_commit_message(commit_message)
        commit_stdout, _ = commit_changes(formatted_message)
        logger.info("Sync: Changes committed.")

    pull_stdout, _ = pull_remote_changes()
    logger.info("Sync: Pull from remote successful.")

    push_stdout, _ = push_local_changes()
    logger.info("Sync: Push to remote successful.")

    full_stdout = (
        f"Add Output:\n{add_stdout}\n\n"
        f"Commit Output:\n{commit_stdout}\n\n"
        f"Pull Output:\n{pull_stdout}\n\n"
        f"Push Output:\n{push_stdout}"
    )
    logger.info("Workspace sync completed successfully.")
    return full_stdout, ""


def get_files_in_commit(commit_hash: str) -> List[Dict[str, str]]:
    _check_repo()
    commit = repo.commit(commit_hash)
    parent = (
        commit.parents[0]
        if commit.parents
        else repo.tree("4b825dc642cb6eb9a060e54bf8d69288fbee4904")
    )
    diffs = commit.diff(parent, create_patch=False)

    changed_files = []
    for diff in diffs:
        status = diff.change_type
        filepath = diff.a_path
        changed_files.append({"status": status, "path": filepath})
    return changed_files


def list_branches() -> Dict[str, Any]:
    """Lists all local and remote branches."""
    _check_repo()

    active_branch_name = get_current_branch()

    all_branches = []

    # Local branches
    for b in repo.branches:
        all_branches.append(
            {
                "name": b.name,
                "is_active": b.name == active_branch_name,
                "is_remote": False,
            }
        )

    # Remote branches
    # We need to be careful not to add duplicates if a local branch tracks a remote one.
    local_branch_names = {b.name for b in repo.branches}
    for r in repo.remotes:
        for ref in r.refs:
            # ref.name is like 'origin/main', we want 'main'
            branch_name_part = ref.name.split("/")[-1]
            if branch_name_part not in local_branch_names:
                all_branches.append(
                    {
                        "name": ref.name,  # Show full remote name like 'origin/main'
                        "is_active": ref.name == active_branch_name,
                        "is_remote": True,
                    }
                )

    return {"branches": all_branches, "current_branch": active_branch_name}


def switch_branch(branch_name: str) -> Tuple[str, str]:
    """Switches to a different local or remote branch."""
    _check_repo()

    try:
        # Check if it's a remote branch
        if "/" in branch_name:
            # For remote branches, we need to check them out as new local tracking branches
            remote_name, remote_branch_name = branch_name.split("/", 1)
            remote = _get_remote(remote_name)

            # Find the corresponding remote ref
            remote_ref = next(
                (ref for ref in remote.refs if ref.name == branch_name), None
            )
            if not remote_ref:
                raise GitPythonError(
                    f"switch {branch_name}",
                    1,
                    f"Remote branch '{branch_name}' not found.",
                    "",
                )

            # Create a local branch that tracks the remote branch
            new_local_branch = repo.create_head(remote_branch_name, remote_ref)
            new_local_branch.set_tracking_branch(remote_ref)
            new_local_branch.checkout()

        else:
            # It's a local branch
            repo.heads[branch_name].checkout()

        return f"Switched to branch '{branch_name}'.", ""
    except KeyError:
        raise GitPythonError(
            f"switch {branch_name}", 1, f"Local branch '{branch_name}' not found.", ""
        )
