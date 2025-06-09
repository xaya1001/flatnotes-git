# server/git_integration/router.py

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional, List

from auth.base import BaseAuth
from global_config import GlobalConfig
from logger import logger

from . import git_utils
from . import config as git_config
from .exceptions import GitCommandError
from .git_models import (
    GitCommandResponse,
    GitStatusResponse,
    GitCommitRequest,
    GitLogResponse,
    GitPullParams,
    GitPushParams,
    GitFileOperationRequest,
    GitStatusSummaryResponse,
    GitFileStatusItem,
)
from .log_handler import add_git_log, get_all_logs, LogLevel, LogEntry
from datetime import datetime
from pydantic import BaseModel


class AutoSyncState(BaseModel):
    paused: bool


main_global_config = GlobalConfig()
auth: Optional[BaseAuth] = main_global_config.load_auth()
auth_deps = [Depends(auth.authenticate)] if auth else []

router = APIRouter()


def check_git_enabled():
    if not git_config.GIT_ENABLED:
        raise HTTPException(
            status_code=503, detail="Git integration is not enabled on the server."
        )
    try:
        if not git_config.GIT_REPO_PATH or not git_utils.os.path.isdir(
            git_config.GIT_REPO_PATH
        ):
            raise HTTPException(
                status_code=500,
                detail=f"Git repository path '{git_config.GIT_REPO_PATH}' is not configured or not a directory.",
            )
    except GitCommandError as e:
        logger.error(f"Git repo check failed: {e.message} - {e.stderr}")
        raise HTTPException(
            status_code=500,
            detail=f"The configured notes directory is not a valid Git repository: {e.stderr or e.message}",
        )


common_deps = auth_deps + [Depends(check_git_enabled)]


@router.get(
    "/activity-log",
    response_model=List[LogEntry],
    dependencies=common_deps,
    summary="Get Git Activity Log",
)
async def get_git_activity_log():
    """Retrieves the most recent Git-related activity logs from the server."""
    return get_all_logs()


@router.get(
    "/status",
    response_model=GitStatusResponse,
    dependencies=common_deps,
    summary="Get Git Repository Status",
)
async def get_git_status():
    try:
        status_data = git_utils.get_status()
        return GitStatusResponse(**status_data)
    except GitCommandError as e:
        logger.error(f"API Error getting Git status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/add_all",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Stage All Changes",
)
async def add_all_git_changes():
    try:
        stdout, stderr = git_utils.add_all_changes()
        message = "All changes added to staging."
        add_git_log(LogLevel.SUCCESS, message, details=stdout or stderr)
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(LogLevel.ERROR, "Failed to stage all changes.", details=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/unstage_all",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Unstage All Changes",
)
async def unstage_all_git_changes():
    """Unstages all currently staged files."""
    try:
        stdout, stderr = git_utils.unstage_all_files()
        message = "All staged changes have been unstaged."
        add_git_log(LogLevel.SUCCESS, message, details=stdout or stderr)
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(LogLevel.ERROR, "Failed to unstage all changes.", details=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stage_file", response_model=GitCommandResponse, dependencies=common_deps)
async def stage_file(request: GitFileOperationRequest):
    try:
        stdout, stderr = git_utils.add_file(request.filepath)
        message = f"File '{request.filepath}' staged."
        add_git_log(LogLevel.SUCCESS, message, details=stdout or stderr)
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(
            LogLevel.ERROR,
            f"Failed to stage file '{request.filepath}'.",
            details=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/unstage_file", response_model=GitCommandResponse, dependencies=common_deps
)
async def unstage_file(request: GitFileOperationRequest):
    try:
        stdout, stderr = git_utils.unstage_file(request.filepath)
        message = f"File '{request.filepath}' unstaged."
        add_git_log(LogLevel.SUCCESS, message, details=stdout or stderr)
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(
            LogLevel.ERROR,
            f"Failed to unstage file '{request.filepath}'.",
            details=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/discard_file", response_model=GitCommandResponse, dependencies=common_deps
)
async def discard_file(request: GitFileOperationRequest):
    try:
        stdout, stderr = git_utils.discard_file_changes(request.filepath)
        message = f"Changes for '{request.filepath}' discarded."
        add_git_log(LogLevel.SUCCESS, message, details=stdout or stderr)
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(
            LogLevel.ERROR,
            f"Failed to discard changes for '{request.filepath}'.",
            details=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/discard_all", response_model=GitCommandResponse, dependencies=common_deps
)
async def discard_all_changes():
    try:
        stdout, stderr = git_utils.discard_all_changes()
        message = "All unstaged changes have been discarded."
        add_git_log(LogLevel.SUCCESS, message, details=stdout or stderr)
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(LogLevel.ERROR, "Failed to discard all changes.", details=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/commit",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Commit Staged Changes",
)
async def commit_git_changes(commit_request: GitCommitRequest = Body(...)):
    try:
        stdout, stderr = git_utils.commit_changes(message=commit_request.message)
        if "No changes staged for commit" in stdout:
            add_git_log(LogLevel.INFO, "Commit: No changes staged.")
            return GitCommandResponse(message=stdout, stdout=stdout, stderr=stderr)

        message = "Changes committed successfully."
        add_git_log(
            LogLevel.SUCCESS,
            message,
            details=f'Message: "{commit_request.message}"\n---\n{stdout or stderr}',
        )
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GitCommandError as e:
        add_git_log(LogLevel.ERROR, "Commit: Failed.", details=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/sync",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Sync Workspace (Add, Commit, Pull, Push)",
)
async def sync_workspace(commit_request: GitCommitRequest = Body(...)):
    try:
        commit_message = (
            commit_request.message
            or f"chore: sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        stdout, stderr = git_utils.sync_workspace(commit_message=commit_message)
        message = "Workspace synchronized successfully."
        # The sync_workspace function is complex, so we log its final output as success.
        # The function itself will raise an error on failure, which is caught below.
        add_git_log(LogLevel.SUCCESS, message, details=stdout)
        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        # The error from sync_workspace is already very descriptive.
        add_git_log(LogLevel.ERROR, "Sync: Failed.", details=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/pull",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Pull Remote Changes",
)
async def pull_git_changes(params: GitPullParams = Depends()):
    try:
        stdout, stderr = git_utils.pull_remote_changes(
            remote=params.remote,
            branch=params.branch,
            rebase=params.rebase,
            autostash=params.autostash,
        )
        message = "Pull operation completed."

        if "Already up to date." in stdout or "Already up to date." in stderr:
            add_git_log(LogLevel.INFO, "Pull: Already up to date.")
        elif stderr:
            add_git_log(LogLevel.WARN, "Pull: Completed with warnings.", details=stderr)
        else:
            add_git_log(LogLevel.SUCCESS, message, details=stdout)

        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(LogLevel.ERROR, "Pull: Failed.", details=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/push",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Push Local Changes",
)
async def push_git_changes(params: GitPushParams = Depends()):
    try:
        stdout, stderr = git_utils.push_local_changes(
            remote=params.remote, branch=params.branch, force=params.force
        )
        message = "Push operation completed."

        if "Everything up-to-date" in stdout or "Everything up-to-date" in stderr:
            add_git_log(LogLevel.INFO, "Push: Everything up-to-date.")
        elif stderr:
            add_git_log(LogLevel.WARN, "Push: Completed with warnings.", details=stderr)
        else:
            add_git_log(LogLevel.SUCCESS, message, details=stdout)

        return GitCommandResponse(message=message, stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        add_git_log(LogLevel.ERROR, "Push: Failed.", details=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/log",
    response_model=GitLogResponse,
    dependencies=common_deps,
    summary="Get Commit Log",
)
async def get_git_log(limit: int = Query(10, ge=1, le=100), page: int = Query(1, ge=1)):
    try:
        log_entries_data = git_utils.get_commit_log(limit=limit, page=page)
        return GitLogResponse(log=log_entries_data, page=page, limit=limit)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status-summary",
    response_model=GitStatusSummaryResponse,
    dependencies=common_deps,
    summary="Get a lightweight Git status summary",
)
async def get_git_status_summary():
    try:
        summary_data = git_utils.get_status_summary()
        return GitStatusSummaryResponse(**summary_data)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/auto-sync/state",
    response_model=AutoSyncState,
    dependencies=common_deps,
    summary="Get Auto-Sync Pause State",
)
async def get_auto_sync_state():
    return AutoSyncState(paused=git_config.is_auto_sync_paused())


@router.post(
    "/auto-sync/pause",
    response_model=AutoSyncState,
    dependencies=common_deps,
    summary="Pause Auto-Sync",
)
async def set_pause_auto_sync():
    git_config.pause_auto_sync()
    add_git_log(LogLevel.INFO, "Auto-sync: Paused by user.")
    return AutoSyncState(paused=True)


@router.post(
    "/auto-sync/resume",
    response_model=AutoSyncState,
    dependencies=common_deps,
    summary="Resume Auto-Sync",
)
async def set_resume_auto_sync():
    git_config.resume_auto_sync()
    add_git_log(LogLevel.INFO, "Auto-sync: Resumed by user.")
    return AutoSyncState(paused=False)


@router.get(
    "/commits/{commit_hash}/files",
    response_model=List[GitFileStatusItem],
    dependencies=common_deps,
    summary="Get Files for a Specific Commit",
)
async def get_commit_files(commit_hash: str):
    try:
        # A = Added, M = Modified, D = Deleted.
        raw_files = git_utils.get_files_in_commit(commit_hash)

        response_files = []
        for f in raw_files:
            response_files.append(
                GitFileStatusItem(
                    path=f["path"], index_status=f["status"], work_tree_status=" "
                )
            )
        return response_files
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))
