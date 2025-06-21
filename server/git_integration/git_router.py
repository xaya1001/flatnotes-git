# server/git_integration/router.py
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response

from auth.base import BaseAuth
from global_config import GlobalConfig
from logger import logger

from . import git_config as git_config
from .git_logger import (
    LogEntry,
    LogLevel,
    add_git_log,
    clear_all_logs,
    get_all_logs,
)
from .git_manager import (
    BranchNotFoundError,
    GitManager,
    GitManagerError,
    MergeConflictError,
    NoChangesError,
    PushRejectedError,
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
    SwitchBranchRequest,
)


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
            pull_strategy=git_config.GIT_PULL_STRATEGY,
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


def handle_git_exception(e: Exception, action: str, manager: GitManager):
    """Centralized exception handler for Git operations."""
    if isinstance(e, MergeConflictError):
        repo_state = manager.get_repository_state()
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Merge Conflict", str(e))
        conflicted_files = manager.get_conflicted_files()
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"A conflict occurred during the '{action}' operation. Please resolve it.",
                "state": repo_state,  # e.g., REBASING_CONFLICT or MERGING_CONFLICT
                "conflicted_files": conflicted_files,
            },
        )
    if isinstance(e, PushRejectedError):
        add_git_log(LogLevel.WARN, f"Failed: {action} - Push Rejected", str(e))
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Push was rejected by the remote because it is not a fast-forward. "
                "This usually means the remote has changes you don't have locally. "
                "Please pull the latest changes and try again.",
                "state": "PUSH_REJECTED_NON_FAST_FORWARD",
            },
        )
    if isinstance(e, (ValueError, NoChangesError)):
        add_git_log(
            LogLevel.WARN,
            f"Skipped: {action}",
            str(e),
            persist=False,
        )
        raise HTTPException(status_code=400, detail=str(e))
    if isinstance(e, (RemoteNotFoundError, BranchNotFoundError)):
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Not Found", str(e))
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, GitManagerError):
        error_message = str(e)
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Git Error", str(e))
        raise HTTPException(status_code=400, detail=error_message)
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
        handle_git_exception(e, "Get Status", manager)


@router.post("/add_all", response_model=GitCommandResponse)
def add_all_git_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.add_all()
        message = "All changes staged."
        add_git_log(LogLevel.INFO, message, persist=False)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Stage All", manager)


@router.post("/unstage_all", response_model=GitCommandResponse)
def unstage_all_git_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.unstage_all()
        message = "All staged changes have been unstaged."
        add_git_log(LogLevel.INFO, message, persist=False)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Unstage All", manager)


@router.post("/stage_file", response_model=GitCommandResponse)
def stage_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.add_file(request.filepath)
        message = f"File '{request.filepath}' staged."
        add_git_log(LogLevel.INFO, message, persist=False)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Stage File '{request.filepath}'", manager)


@router.post("/unstage_file", response_model=GitCommandResponse)
def unstage_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.unstage_file(request.filepath)
        message = f"File '{request.filepath}' unstaged."
        add_git_log(LogLevel.INFO, message, persist=False)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Unstage File '{request.filepath}'", manager)


@router.post("/discard_file", response_model=GitCommandResponse)
def discard_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.discard_file(request.filepath)
        message = f"Changes for '{request.filepath}' discarded."
        add_git_log(LogLevel.WARN, message, persist=False)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Discard File '{request.filepath}'", manager)


@router.post("/discard_all", response_model=GitCommandResponse)
def discard_all_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.discard_all()
        message = "All unstaged changes have been discarded."
        add_git_log(LogLevel.WARN, message, "This is a destructive operation.")
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Discard All", manager)


@router.post("/commit", response_model=GitCommandResponse)
def commit_git_changes(
    commit_request: GitCommitRequest = Body(...),
    manager: GitManager = Depends(get_git_manager),
):
    try:
        commit_result = manager.commit(message=commit_request.message)
        message = "Changes committed successfully."
        add_git_log(
            LogLevel.SUCCESS,
            message,
            details=commit_result,
        )
        return GitCommandResponse(message=message, details=commit_result)
    except Exception as e:
        handle_git_exception(e, "Commit", manager)


@router.post("/pull", response_model=GitCommandResponse)
def pull_git_changes(
    params: GitPullParams = Depends(), manager: GitManager = Depends(get_git_manager)
):
    try:
        result = manager.pull_remote_changes(
            remote_name=params.remote, branch=params.branch
        )
        message = "Pull operation completed."
        add_git_log(LogLevel.SUCCESS, message, details=result)
        return GitCommandResponse(message=message, details=result)
    except Exception as e:
        handle_git_exception(e, "Pull", manager)


@router.post("/push", response_model=GitCommandResponse)
def push_git_changes(
    params: GitPushParams = Depends(), manager: GitManager = Depends(get_git_manager)
):
    try:
        result = manager.push_local_changes(
            remote_name=params.remote, branch=params.branch, force=params.force
        )
        message = "Push operation completed."
        add_git_log(LogLevel.SUCCESS, message, details=result)
        return GitCommandResponse(message=message, details=result)
    except Exception as e:
        handle_git_exception(e, "Push", manager)


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
                details={"default_message": commit_message},
                persist=False,
            )
        else:
            commit_message = commit_request.message

        results = manager.sync_workspace(commit_message=commit_message)
        message = "Workspace synchronized successfully."
        add_git_log(LogLevel.SUCCESS, message, details=results)
        return GitCommandResponse(message=message, details=results)
    except Exception as e:
        handle_git_exception(e, "Sync Workspace", manager)


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
        handle_git_exception(e, "Get Log", manager)


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
        handle_git_exception(e, f"Get Files for Commit {commit_hash[:7]}", manager)


@router.get("/branches", response_model=BranchListResponse)
def get_branches(manager: GitManager = Depends(get_git_manager)):
    try:
        return manager.fetch_and_list_branches()
    except Exception as e:
        handle_git_exception(e, "List Branches", manager)


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
        handle_git_exception(e, f"Switch Branch to '{request.branch_name}'", manager)


@router.post("/conflict/continue", response_model=GitCommandResponse)
def conflict_continue(manager: GitManager = Depends(get_git_manager)):
    action_name = "Continue Operation"
    try:
        result = manager.continue_conflict_resolution()
        message = result.get("message", "Operation continued successfully.")
        add_git_log(LogLevel.SUCCESS, message, details=result)
        return GitCommandResponse(message=message, details=result)
    except Exception as e:
        handle_git_exception(e, action_name, manager)


@router.post("/conflict/abort", response_model=GitCommandResponse)
def conflict_abort(manager: GitManager = Depends(get_git_manager)):
    action_name = "Abort Operation"
    try:
        output = manager.abort_conflict_resolution()
        message = "Operation aborted successfully."
        add_git_log(LogLevel.WARN, message, details={"raw_output": output})
        return GitCommandResponse(message=message, stdout=output)
    except Exception as e:
        handle_git_exception(e, action_name, manager)


# --- Management Endpoints ---


@router.get("/activity-log", response_model=List[LogEntry], dependencies=auth_deps)
def get_git_activity_log():
    return get_all_logs()


@router.delete("/activity-log", status_code=204, dependencies=auth_deps)
def delete_git_activity_log():
    """Deletes all persisted git activity logs."""
    try:
        clear_all_logs()
        # Per HTTP spec, a 204 response should not contain a body.
        return Response(status_code=204)
    except Exception as e:
        # Avoid the generic handler so we don't add a new log entry
        # right after clearing them.
        logger.error(f"Failed to clear activity logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear activity logs.")


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
    action_name = "Reset to Remote"
    try:
        result = manager.reset_to_remote()
        add_git_log(
            LogLevel.WARN,
            "Local branch was hard reset to remote state.",
            details=result,
        )
        return GitCommandResponse(message=result.get("message"), details=result)
    except Exception as e:
        handle_git_exception(e, action_name, manager)


@router.post("/restore-file", response_model=GitCommandResponse)
def restore_file_from_commit(
    request: GitRestoreFileRequest, manager: GitManager = Depends(get_git_manager)
):
    action_name = f"Restore file '{request.filepath}'"
    try:
        manager.checkout_file_from_commit(request.commit_hash, request.filepath)
        message = f"File '{request.filepath}' restored to state from commit {request.commit_hash[:7]}."
        add_git_log(LogLevel.WARN, message, "Working directory file was overwritten.")
        return GitCommandResponse(message=message)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        handle_git_exception(e, action_name, manager)
