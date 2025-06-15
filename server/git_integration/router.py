# server/git_integration/router.py
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth.base import BaseAuth
from global_config import GlobalConfig
from logger import logger

from . import config as git_config
from .git_manager import (
    BranchNotFoundError,
    GitManager,
    GitManagerError,
    MergeConflictError,
    NoChangesError,
    RemoteNotFoundError,
    RepositoryInvalidError,
)
from .git_models import (
    BranchListResponse,
    GitCommandResponse,
    GitCommitRequest,
    GitFileOperationRequest,
    GitFileStatusItem,
    GitLogResponse,
    GitPullParams,
    GitPushParams,
    GitRestoreFileRequest,
    GitStatusResponse,
    GitStatusSummaryResponse,
    SwitchBranchRequest,
)
from .log_handler import LogEntry, LogLevel, add_git_log, get_all_logs


# --- Dependency Injection ---
def get_git_manager() -> GitManager:
    if not git_config.GIT_ENABLED:
        raise HTTPException(
            status_code=503, detail="Git integration is not enabled on the server."
        )
    try:
        return GitManager(
            repo_path=git_config.GIT_REPO_PATH,
            default_branch=git_config.GIT_DEFAULT_BRANCH,
            default_remote=git_config.GIT_REMOTE_NAME,
            user_name=git_config.GIT_COMMIT_USER_NAME,
            user_email=git_config.GIT_COMMIT_USER_EMAIL,
        )
    except RepositoryInvalidError as e:
        logger.error(f"Git repo check failed on dependency creation: {e}")
        raise HTTPException(status_code=428, detail=str(e))


# --- Router Setup ---
main_global_config = GlobalConfig()
auth: Optional[BaseAuth] = main_global_config.load_auth()
auth_deps = [Depends(auth.authenticate)] if auth else []
common_deps = auth_deps + [Depends(get_git_manager)]
router = APIRouter(dependencies=common_deps)


def handle_git_exception(e: Exception, action: str):
    """Centralized exception handler for Git operations."""
    if isinstance(e, MergeConflictError):
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Merge Conflict", str(e))
        raise HTTPException(status_code=409, detail=str(e))
    if isinstance(e, (ValueError, NoChangesError)):
        add_git_log(
            LogLevel.WARN, f"Skipped: {action} - No Changes or Bad Request", str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    if isinstance(e, (RemoteNotFoundError, BranchNotFoundError)):
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Not Found", str(e))
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, GitManagerError):
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Git Error", str(e))
        raise HTTPException(status_code=500, detail=f"A Git error occurred: {e}")
    # Catch-all for unexpected errors
    logger.error(f"Unexpected error during '{action}': {e}", exc_info=True)
    add_git_log(LogLevel.ERROR, f"Failed: {action} - Unexpected Server Error", str(e))
    raise HTTPException(
        status_code=500, detail=f"An unexpected server error occurred: {e}"
    )


# --- API Endpoints ---


@router.get("/status", response_model=GitStatusResponse)
def get_git_status(manager: GitManager = Depends(get_git_manager)):
    try:
        return manager.get_status()
    except Exception as e:
        handle_git_exception(e, "Get Status")


@router.post("/add_all", response_model=GitCommandResponse)
def add_all_git_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.add_all()
        message = "All changes staged."
        add_git_log(LogLevel.SUCCESS, message)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Stage All")


@router.post("/unstage_all", response_model=GitCommandResponse)
def unstage_all_git_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.unstage_all()
        message = "All staged changes have been unstaged."
        add_git_log(LogLevel.SUCCESS, message)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Unstage All")


@router.post("/stage_file", response_model=GitCommandResponse)
def stage_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.add_file(request.filepath)
        message = f"File '{request.filepath}' staged."
        add_git_log(LogLevel.SUCCESS, message)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Stage File '{request.filepath}'")


@router.post("/unstage_file", response_model=GitCommandResponse)
def unstage_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.unstage_file(request.filepath)
        message = f"File '{request.filepath}' unstaged."
        add_git_log(LogLevel.SUCCESS, message)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Unstage File '{request.filepath}'")


@router.post("/discard_file", response_model=GitCommandResponse)
def discard_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.discard_file(request.filepath)
        message = f"Changes for '{request.filepath}' discarded."
        add_git_log(LogLevel.WARN, message)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Discard File '{request.filepath}'")


@router.post("/discard_all", response_model=GitCommandResponse)
def discard_all_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.discard_all()
        message = "All unstaged changes have been discarded."
        add_git_log(LogLevel.WARN, message, "This is a destructive operation.")
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Discard All")


@router.post("/commit", response_model=GitCommandResponse)
def commit_git_changes(
    commit_request: GitCommitRequest = Body(...),
    manager: GitManager = Depends(get_git_manager),
):
    try:
        commit_hash = manager.commit(message=commit_request.message)
        message = "Changes committed successfully."
        add_git_log(
            LogLevel.SUCCESS,
            message,
            details=f'Commit: {commit_hash}\nMessage: "{commit_request.message}"',
        )
        return GitCommandResponse(message=message, details={"commitHash": commit_hash})
    except Exception as e:
        handle_git_exception(e, "Commit")


@router.post("/pull", response_model=GitCommandResponse)
def pull_git_changes(
    params: GitPullParams = Depends(), manager: GitManager = Depends(get_git_manager)
):
    try:
        result = manager.pull_remote_changes(
            remote_name=params.remote,
            branch=params.branch,
            rebase=params.rebase,
        )
        message = "Pull operation completed."

        log_details = result.get("message", "").strip()
        changed_files = result.get("changed_files", [])
        if changed_files:
            file_list_str = "\n".join(
                f"  - {file['change_type']}: {file['path']}" for file in changed_files
            )
            log_details += f"\n\nUpdated files ({len(changed_files)}):\n{file_list_str}"

        add_git_log(LogLevel.SUCCESS, message, details=log_details)
        return GitCommandResponse(
            message=message, stdout=result.get("message"), details=result
        )
    except Exception as e:
        handle_git_exception(e, "Pull")


@router.post("/push", response_model=GitCommandResponse)
def push_git_changes(
    params: GitPushParams = Depends(), manager: GitManager = Depends(get_git_manager)
):
    try:
        output = manager.push_local_changes(
            remote_name=params.remote, branch=params.branch, force=params.force
        )
        message = "Push operation completed."
        add_git_log(LogLevel.SUCCESS, message, details=output)
        return GitCommandResponse(message=message, stdout=output)
    except Exception as e:
        handle_git_exception(e, "Push")


@router.post("/sync", response_model=GitCommandResponse)
def sync_workspace(
    commit_request: Optional[GitCommitRequest] = Body(None),
    manager: GitManager = Depends(get_git_manager),
):
    try:
        # If no request body or message is provided, create a default one.
        if not commit_request or not commit_request.message.strip():
            commit_message = (
                f"chore: sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            add_git_log(
                LogLevel.INFO,
                "No commit message provided, using default.",
                details=commit_message,
            )
        else:
            commit_message = commit_request.message

        results = manager.sync_workspace(commit_message=commit_message)
        message = "Workspace synchronized successfully."

        # This logging logic can be improved, but is fine for now
        commit_info = results.get("commit", {})
        pull_info = results.get("pull", {})
        push_info = results.get("push", {})

        log_details_parts = []
        if commit_info.get("hash") != "no_changes":
            log_details_parts.append(f"Commit: {commit_info.get('hash', 'N/A')}")
        else:
            log_details_parts.append("Commit: No changes to commit.")

        if pull_info.get("changed_files"):
            log_details_parts.append(
                f"Pull: {len(pull_info['changed_files'])} file(s) updated."
            )
        else:
            log_details_parts.append(f"Pull: No new changes from remote.")

        log_details_parts.append(f"Push: {push_info.get('message', 'N/A').strip()}")

        add_git_log(LogLevel.SUCCESS, message, details="\n".join(log_details_parts))
        return GitCommandResponse(message=message, details=results)
    except Exception as e:
        handle_git_exception(e, "Sync Workspace")


@router.get("/log", response_model=GitLogResponse)
def get_git_log(
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    manager: GitManager = Depends(get_git_manager),
):
    try:
        log_entries = manager.get_commit_log(limit=limit, page=page)
        remote_url = manager.get_remote_url()
        web_url = manager._format_remote_url_for_web(remote_url)

        return GitLogResponse(
            log=log_entries, page=page, limit=limit, remote_base_url=web_url
        )
    except Exception as e:
        handle_git_exception(e, "Get Log")


@router.get("/status-summary", response_model=GitStatusSummaryResponse)
def get_git_status_summary(manager: GitManager = Depends(get_git_manager)):
    try:
        return manager.get_status_summary()
    except Exception as e:
        handle_git_exception(e, "Get Status Summary")


@router.get("/commits/{commit_hash}/files", response_model=List[GitFileStatusItem])
def get_commit_files(commit_hash: str, manager: GitManager = Depends(get_git_manager)):
    try:
        raw_files = manager.get_files_in_commit(commit_hash)
        return [
            GitFileStatusItem(
                path=f["path"], index_status=f["status"], work_tree_status=" "
            )
            for f in raw_files
        ]
    except Exception as e:
        handle_git_exception(e, f"Get Files for Commit {commit_hash[:7]}")


@router.get("/branches", response_model=BranchListResponse)
def get_branches(manager: GitManager = Depends(get_git_manager)):
    try:
        return manager.fetch_and_list_branches()
    except Exception as e:
        handle_git_exception(e, "List Branches")


@router.post("/branches/switch", response_model=GitCommandResponse)
def switch_to_branch(
    request: SwitchBranchRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.switch_branch(request.branch_name)
        message = f"Successfully switched to branch '{request.branch_name}'."
        add_git_log(LogLevel.SUCCESS, message)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Switch Branch to '{request.branch_name}'")


# --- Management Endpoints ---


@router.get("/activity-log", response_model=List[LogEntry], dependencies=auth_deps)
def get_git_activity_log():
    return get_all_logs()


@router.get("/auto-sync/state", response_model=dict, dependencies=auth_deps)
def get_auto_sync_state():
    return {"paused": git_config.is_auto_sync_paused()}


@router.post("/auto-sync/pause", response_model=dict, dependencies=auth_deps)
def set_pause_auto_sync():
    git_config.pause_auto_sync()
    add_git_log(LogLevel.INFO, "Auto-sync: Paused by user.")
    return {"paused": True}


@router.post("/auto-sync/resume", response_model=dict, dependencies=auth_deps)
def set_resume_auto_sync():
    git_config.resume_auto_sync()
    add_git_log(LogLevel.INFO, "Auto-sync: Resumed by user.")
    return {"paused": False}


@router.post("/reset-to-remote", response_model=GitCommandResponse)
def reset_to_remote(manager: GitManager = Depends(get_git_manager)):
    """
    Resets the current branch to its upstream/remote counterpart.
    This is a destructive operation and will discard all local changes and unpushed commits.
    """
    action_name = "Reset to Remote"
    try:
        result = manager.reset_to_remote()
        add_git_log(
            LogLevel.WARN,
            "Local branch was hard reset to remote state.",
            details=str(result),
        )
        return GitCommandResponse(message=result.get("message"), details=result)
    except Exception as e:
        handle_git_exception(e, action_name)


@router.post("/restore-file", response_model=GitCommandResponse)
def restore_file_from_commit(
    request: GitRestoreFileRequest, manager: GitManager = Depends(get_git_manager)
):
    """
    Restores a specific file in the working directory to its state from a given commit.
    """
    action_name = f"Restore file '{request.filepath}'"
    try:
        manager.checkout_file_from_commit(request.commit_hash, request.filepath)
        message = f"File '{request.filepath}' restored to state from commit {request.commit_hash[:7]}."
        add_git_log(LogLevel.WARN, message, "Working directory file was overwritten.")
        return GitCommandResponse(message=message)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        handle_git_exception(e, action_name)
