# server/git_integration/router.py
import asyncio
from datetime import datetime
from functools import lru_cache
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from starlette.responses import StreamingResponse

from auth.base import BaseAuth
from global_config import GlobalConfig
from logger import logger

from . import config as git_config
from .event_broadcaster import broadcaster
from .git_manager import (
    BranchNotFoundError,
    GitManager,
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
    GitStatusResponse,
    GitStatusSummaryResponse,
    SwitchBranchRequest,
)
from .log_handler import LogEntry, LogLevel, add_git_log, get_all_logs


# --- Dependency Injection ---
@lru_cache()
def get_git_manager() -> GitManager:
    """Dependency to create and cache a singleton GitManager instance."""
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
        raise HTTPException(status_code=500, detail=str(e))


# --- Router Setup ---
main_global_config = GlobalConfig()
auth: Optional[BaseAuth] = main_global_config.load_auth()
auth_deps = [Depends(auth.authenticate)] if auth else []
common_deps = auth_deps + [Depends(get_git_manager)]
router = APIRouter(dependencies=common_deps)


def handle_git_exception(e: Exception, action: str):
    """Centralized exception handler for the router."""
    if isinstance(e, MergeConflictError):
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Merge Conflict", str(e))
        raise HTTPException(status_code=409, detail=str(e))
    if isinstance(e, (ValueError, NoChangesError)):
        add_git_log(LogLevel.WARN, f"Skipped: {action} - Bad Request", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    if isinstance(e, (RemoteNotFoundError, BranchNotFoundError)):
        add_git_log(LogLevel.ERROR, f"Failed: {action} - Not Found", str(e))
        raise HTTPException(status_code=404, detail=str(e))
    # Catch-all for other Git errors
    add_git_log(LogLevel.ERROR, f"Failed: {action} - Server Error", str(e))
    raise HTTPException(
        status_code=500, detail=f"An unexpected Git error occurred: {e}"
    )


# --- NEW SSE ENDPOINT ---
@router.get("/events", dependencies=auth_deps)
async def sse_events(request: Request):
    """Server-Sent Events endpoint to stream real-time updates to clients."""
    queue = asyncio.Queue()
    await broadcaster.connect(queue)

    async def event_generator():
        try:
            while True:
                message = await queue.get()
                if await request.is_disconnected():
                    break
                yield f"event: {message['event']}\ndata: {message['data']}\n\n"
        finally:
            broadcaster.disconnect(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def broadcast_updates(manager: GitManager):
    """Helper function to broadcast all necessary updates after an action."""
    # Get the FULL, fresh status
    full_status = manager.get_status()
    # The summary is just a part of the full status
    summary = {
        "current_branch": full_status["current_branch"],
        "files_changed_count": len(full_status["files"]),
    }

    # Broadcast the full status payload
    await broadcaster.broadcast("status_update", full_status)

    # Broadcast the summary separately for the indicator
    await broadcaster.broadcast("summary_update", summary)

    # Broadcast a log update
    latest_logs = get_all_logs()
    await broadcaster.broadcast("log_update", [log.dict() for log in latest_logs])


# --- Refactored Endpoints ---
@router.get("/status", response_model=GitStatusResponse)
async def get_git_status(manager: GitManager = Depends(get_git_manager)):
    return manager.get_status()


@router.post("/add_all", response_model=GitCommandResponse)
async def add_all_git_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.add_all()
        message = "All changes staged."
        add_git_log(LogLevel.SUCCESS, message)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Stage All")


@router.post("/unstage_all", response_model=GitCommandResponse)
async def unstage_all_git_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.unstage_all()
        message = "All staged changes have been unstaged."
        add_git_log(LogLevel.SUCCESS, message)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Unstage All")


@router.post("/stage_file", response_model=GitCommandResponse)
async def stage_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.add_file(request.filepath)
        message = f"File '{request.filepath}' staged."
        add_git_log(LogLevel.SUCCESS, message)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Stage File '{request.filepath}'")


@router.post("/unstage_file", response_model=GitCommandResponse)
async def unstage_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.unstage_file(request.filepath)
        message = f"File '{request.filepath}' unstaged."
        add_git_log(LogLevel.SUCCESS, message)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Unstage File '{request.filepath}'")


@router.post("/discard_file", response_model=GitCommandResponse)
async def discard_file(
    request: GitFileOperationRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.discard_file(request.filepath)
        message = f"Changes for '{request.filepath}' discarded."
        add_git_log(LogLevel.SUCCESS, message)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Discard File '{request.filepath}'")


@router.post("/discard_all", response_model=GitCommandResponse)
async def discard_all_changes(manager: GitManager = Depends(get_git_manager)):
    try:
        manager.discard_all()
        message = "All unstaged changes have been discarded."
        add_git_log(LogLevel.SUCCESS, message)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, "Discard All")


@router.post("/commit", response_model=GitCommandResponse)
async def commit_git_changes(
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
        await broadcast_updates(manager)
        return GitCommandResponse(message=message, details={"commitHash": commit_hash})
    except Exception as e:
        handle_git_exception(e, "Commit")


@router.post("/sync", response_model=GitCommandResponse)
async def sync_workspace(
    commit_request: GitCommitRequest = Body(...),
    manager: GitManager = Depends(get_git_manager),
):
    try:
        commit_message = (
            commit_request.message
            or f"chore: sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        results = manager.sync_workspace(commit_message=commit_message)
        message = "Workspace synchronized successfully."
        add_git_log(LogLevel.SUCCESS, message, details=str(results))
        await broadcast_updates(manager)
        return GitCommandResponse(message=message, details=results)
    except Exception as e:
        handle_git_exception(e, "Sync Workspace")


@router.post("/pull", response_model=GitCommandResponse)
async def pull_git_changes(
    params: GitPullParams = Depends(), manager: GitManager = Depends(get_git_manager)
):
    try:
        output = manager.pull_remote_changes(
            remote_name=params.remote,
            branch=params.branch,
            rebase=params.rebase,
        )
        message = "Pull operation completed."
        if "Already up to date" in output:
            add_git_log(LogLevel.INFO, "Pull: Already up to date.")
        else:
            add_git_log(LogLevel.SUCCESS, message, details=output)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message, stdout=output)
    except Exception as e:
        handle_git_exception(e, "Pull")


@router.post("/push", response_model=GitCommandResponse)
async def push_git_changes(
    params: GitPushParams = Depends(), manager: GitManager = Depends(get_git_manager)
):
    try:
        output = manager.push_local_changes(
            remote_name=params.remote, branch=params.branch, force=params.force
        )
        message = "Push operation completed."
        if "Everything up-to-date" in output:
            add_git_log(LogLevel.INFO, "Push: Everything up-to-date.")
        else:
            add_git_log(LogLevel.SUCCESS, message, details=output)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message, stdout=output)
    except Exception as e:
        handle_git_exception(e, "Push")


@router.get("/log", response_model=GitLogResponse)
async def get_git_log(
    limit: int = Query(10, ge=1, le=100),
    page: int = Query(1, ge=1),
    manager: GitManager = Depends(get_git_manager),
):
    try:
        log_entries_data = manager.get_commit_log(limit=limit, page=page)
        return GitLogResponse(log=log_entries_data, page=page, limit=limit)
    except Exception as e:
        handle_git_exception(e, "Get Log")


@router.get("/status-summary", response_model=GitStatusSummaryResponse)
async def get_git_status_summary(manager: GitManager = Depends(get_git_manager)):
    return manager.get_status_summary()


@router.get("/activity-log", response_model=List[LogEntry], dependencies=auth_deps)
async def get_git_activity_log():
    """Retrieves the most recent Git-related activity logs from the server."""
    return get_all_logs()


@router.get("/auto-sync/state", response_model=dict, dependencies=auth_deps)
async def get_auto_sync_state():
    return {"paused": git_config.is_auto_sync_paused()}


@router.post("/auto-sync/pause", response_model=dict, dependencies=auth_deps)
async def set_pause_auto_sync(manager: GitManager = Depends(get_git_manager)):
    git_config.pause_auto_sync()
    add_git_log(LogLevel.INFO, "Auto-sync: Paused by user.")
    await broadcast_updates(manager)
    return {"paused": True}


@router.post("/auto-sync/resume", response_model=dict, dependencies=auth_deps)
async def set_resume_auto_sync(manager: GitManager = Depends(get_git_manager)):
    git_config.resume_auto_sync()
    add_git_log(LogLevel.INFO, "Auto-sync: Resumed by user.")
    await broadcast_updates(manager)
    return {"paused": False}


@router.get("/commits/{commit_hash}/files", response_model=List[GitFileStatusItem])
async def get_commit_files(
    commit_hash: str, manager: GitManager = Depends(get_git_manager)
):
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
async def get_branches(manager: GitManager = Depends(get_git_manager)):
    try:
        # Call the new method that fetches first
        return manager.fetch_and_list_branches()
    except Exception as e:
        handle_git_exception(e, "List Branches")


@router.post("/branches/switch", response_model=GitCommandResponse)
async def switch_to_branch(
    request: SwitchBranchRequest, manager: GitManager = Depends(get_git_manager)
):
    try:
        manager.switch_branch(request.branch_name)
        message = f"Successfully switched to branch '{request.branch_name}'."
        add_git_log(LogLevel.SUCCESS, message)
        await broadcast_updates(manager)
        return GitCommandResponse(message=message)
    except Exception as e:
        handle_git_exception(e, f"Switch Branch to '{request.branch_name}'")
