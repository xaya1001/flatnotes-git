# server/git_integration/git_router.py
import asyncio
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)

from logger import logger
from main import auth

from . import git_config
from .core.git_exceptions import (
    BranchNotFoundError,
    GitManagerError,
    MergeConflictError,
    NoChangesError,
    PushRejectedError,
    RemoteNotFoundError,
)
from .core.git_service import GitService
from .git_logger import (
    LogEntry,
    LogLevel,
    add_git_log,
    clear_all_logs,
    get_all_logs,
)
from .git_models import (
    BranchListResponse,
    GitCommandResponse,
    GitCommitRequest,
    GitFileOperationRequest,
    GitFileStatusItem,
    GitLogResponse,
    GitRestoreFileRequest,
    GitStatusResponse,
    SwitchBranchRequest,
)
from .websockets import connection_manager

# --- Concurrency Lock ---
git_operation_lock = asyncio.Lock()


# --- Dependency Injection (Singleton Pattern) ---
def get_git_service(request: Request) -> GitService:
    """Dependency to get the singleton instance of the GitService from app state."""
    if not git_config.GIT_ENABLED:
        raise HTTPException(
            status_code=503, detail="Git integration is not enabled on the server."
        )

    # Retrieve the singleton instance from the app state
    service = getattr(request.app.state, "git_service", None)
    if service is None:
        # This will be triggered if the service failed to initialize on startup
        raise HTTPException(
            status_code=428,
            detail="Git service is not available. Check server logs for initialization errors.",
        )
    return service


# --- Router Setup ---
auth_deps = [Depends(auth.authenticate)] if auth else []
router = APIRouter(dependencies=auth_deps)


def handle_git_exception(e: Exception, action: str, service: GitService):
    """Centralized exception handler for Git operations."""
    if isinstance(e, MergeConflictError):
        repo_state = service.repository.get_repository_state()
        conflicted_files = service.repository.get_conflicted_files()
        add_git_log(LogLevel.WARN, f"Conflict: {action}", str(e))
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"A conflict occurred during '{action}'. Please resolve it.",
                "state": repo_state,
                "conflicted_files": conflicted_files,
            },
        )
    if isinstance(e, PushRejectedError):
        add_git_log(LogLevel.WARN, f"Push Rejected: {action}", str(e))
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Push was rejected by the remote. Please pull the latest changes.",
                "state": "PUSH_REJECTED_NON_FAST_FORWARD",
            },
        )
    if isinstance(e, (ValueError, NoChangesError)):
        add_git_log(LogLevel.INFO, f"Skipped: {action}", str(e), persist=False)
        raise HTTPException(status_code=400, detail=str(e))
    if isinstance(e, (RemoteNotFoundError, BranchNotFoundError)):
        add_git_log(LogLevel.ERROR, f"Not Found: {action}", str(e))
        raise HTTPException(status_code=404, detail=str(e))
    # This is the new part from the previous fix, which is still relevant
    if isinstance(e, KeyError):
        add_git_log(LogLevel.ERROR, f"Not Found: {action}", str(e))
        raise HTTPException(status_code=404, detail=str(e))
    if isinstance(e, GitManagerError):
        add_git_log(LogLevel.ERROR, f"Failed: {action}", str(e))
        raise HTTPException(status_code=400, detail=str(e))

    logger.error(f"Unexpected error during '{action}': {e}", exc_info=True)
    add_git_log(LogLevel.ERROR, f"Unexpected Server Error: {action}", str(e))
    raise HTTPException(status_code=500, detail=f"An unexpected server error: {e}")


# --- API Endpoints ---


@router.post("/restore-file", response_model=GitCommandResponse)
async def restore_file_from_commit(
    background_tasks: BackgroundTasks,
    request: GitRestoreFileRequest,
    service: GitService = Depends(get_git_service),
):
    action_name = f"Restore file '{request.filepath}'"
    async with git_operation_lock:
        try:
            service.checkout_file_from_commit(request.commit_hash, request.filepath)
            message = f"File '{request.filepath}' restored from commit {request.commit_hash[:7]}."
            add_git_log(
                LogLevel.WARN, message, "Working directory file was overwritten."
            )
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except (
            FileNotFoundError,
            KeyError,
        ) as e:  # Catch both a file system not found and a key not found in tree
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, action_name, service)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, action_name, service)


# ... [ The rest of git_router.py remains the same as the previous correct version ] ...
# For completeness, here's the full git_router.py file again.


@router.get("/status", response_model=GitStatusResponse)
def get_git_status(service: GitService = Depends(get_git_service)):
    # Read operations do not need the lock
    try:
        return service.get_status()
    except Exception as e:
        handle_git_exception(e, "Get Status", service)


@router.post("/add_all", response_model=GitCommandResponse)
async def add_all_git_changes(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            service.add_all()
            message = "All changes staged."
            add_git_log(LogLevel.INFO, message, persist=False)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, "Stage All", service)


@router.post("/unstage_all", response_model=GitCommandResponse)
async def unstage_all_git_changes(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            service.unstage_all()
            message = "All staged changes have been unstaged."
            add_git_log(LogLevel.INFO, message, persist=False)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, "Unstage All", service)


@router.post("/stage_file", response_model=GitCommandResponse)
async def stage_file(
    background_tasks: BackgroundTasks,
    request: GitFileOperationRequest,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            service.add_file(request.filepath)
            message = f"File '{request.filepath}' staged."
            add_git_log(LogLevel.INFO, message, persist=False)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, f"Stage File '{request.filepath}'", service)


@router.post("/unstage_file", response_model=GitCommandResponse)
async def unstage_file(
    background_tasks: BackgroundTasks,
    request: GitFileOperationRequest,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            service.unstage_file(request.filepath)
            message = f"File '{request.filepath}' unstaged."
            add_git_log(LogLevel.INFO, message, persist=False)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, f"Unstage File '{request.filepath}'", service)


@router.post("/discard_file", response_model=GitCommandResponse)
async def discard_file(
    background_tasks: BackgroundTasks,
    request: GitFileOperationRequest,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            service.discard_file(request.filepath)
            message = f"Changes for '{request.filepath}' discarded."
            add_git_log(LogLevel.WARN, message, persist=False)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, f"Discard File '{request.filepath}'", service)


@router.post("/discard_all", response_model=GitCommandResponse)
async def discard_all_changes(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            service.discard_all()
            message = "All unstaged changes have been discarded."
            add_git_log(LogLevel.WARN, message, "This is a destructive operation.")
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, "Discard All", service)


@router.post("/commit", response_model=GitCommandResponse)
async def commit_git_changes(
    background_tasks: BackgroundTasks,
    commit_request: GitCommitRequest = Body(...),
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            commit_result = service.commit(message=commit_request.message)
            message = "Changes committed successfully."
            add_git_log(LogLevel.SUCCESS, message, details=commit_result)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message, details=commit_result)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, "Commit", service)


@router.post("/pull", response_model=GitCommandResponse)
async def pull_git_changes(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            result = service.pull()
            message = "Pull operation completed."
            add_git_log(LogLevel.SUCCESS, message, details=result)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message, details=result)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, "Pull", service)


@router.post("/push", response_model=GitCommandResponse)
async def push_git_changes(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            result = service.push()
            message = "Push operation completed."
            add_git_log(LogLevel.SUCCESS, message, details=result)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message, details=result)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, "Push", service)


@router.post("/sync", response_model=GitCommandResponse)
async def commit_and_sync(
    background_tasks: BackgroundTasks,
    commit_request: Optional[GitCommitRequest] = Body(None),
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            # The frontend now guarantees a non-empty message.
            commit_message = commit_request.message if commit_request else ""
            if not commit_message.strip():
                raise HTTPException(
                    status_code=400, detail="Commit message cannot be empty."
                )

            results = service.sync_workspace(commit_message=commit_message)
            message = "Workspace synchronized successfully."
            add_git_log(LogLevel.SUCCESS, message, details=results)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message, details=results)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, "Sync Workspace", service)


@router.get("/log", response_model=GitLogResponse)
def get_git_log(
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    service: GitService = Depends(get_git_service),
):
    try:
        log_entries = service.get_commit_history(limit=limit, page=page)
        remote_url = service.repository.get_remote_url()
        web_url = service.repository._format_remote_url_for_web(remote_url)
        return GitLogResponse(
            log=log_entries, page=page, limit=limit, remote_base_url=web_url
        )
    except Exception as e:
        handle_git_exception(e, "Get Log", service)


@router.get("/commits/{commit_hash}/files", response_model=List[GitFileStatusItem])
def get_commit_files(commit_hash: str, service: GitService = Depends(get_git_service)):
    try:
        raw_files = service.get_files_in_commit(commit_hash)
        return [
            GitFileStatusItem(
                path=f.get("path"),
                index_status=f.get("status"),
                work_tree_status=" ",
                original_path=f.get("old_path"),
            )
            for f in raw_files
        ]
    except Exception as e:
        handle_git_exception(e, f"Get Files for Commit {commit_hash[:7]}", service)


@router.get("/branches", response_model=BranchListResponse)
def get_branches(service: GitService = Depends(get_git_service)):
    try:
        return service.list_branches()
    except Exception as e:
        handle_git_exception(e, "List Branches", service)


@router.post("/branches/switch", response_model=GitCommandResponse)
async def switch_to_branch(
    background_tasks: BackgroundTasks,
    request: SwitchBranchRequest,
    service: GitService = Depends(get_git_service),
):
    async with git_operation_lock:
        try:
            service.switch_branch(request.branch_name)
            message = f"Successfully switched to branch '{request.branch_name}'."
            add_git_log(LogLevel.SUCCESS, message)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(
                e, f"Switch Branch to '{request.branch_name}'", service
            )


@router.post("/conflict/continue", response_model=GitCommandResponse)
async def conflict_continue(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    action_name = "Continue Operation"
    async with git_operation_lock:
        try:
            result = service.resolve_conflict("continue")
            message = result.get("message", "Operation continued successfully.")
            add_git_log(LogLevel.SUCCESS, message, details=result)
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message, details=result)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, action_name, service)


@router.post("/conflict/abort", response_model=GitCommandResponse)
async def conflict_abort(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    action_name = "Abort Operation"
    async with git_operation_lock:
        try:
            result = service.resolve_conflict("abort")
            message = result.get("message", "Operation aborted.")
            add_git_log(
                LogLevel.WARN, message, details={"raw_output": result.get("stdout")}
            )
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=message, stdout=result.get("stdout"))
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, action_name, service)


@router.post("/reset-to-remote", response_model=GitCommandResponse)
async def reset_to_remote(
    background_tasks: BackgroundTasks,
    service: GitService = Depends(get_git_service),
):
    action_name = "Reset to Remote"
    async with git_operation_lock:
        try:
            result = service.reset_to_remote()
            add_git_log(
                LogLevel.WARN,
                "Local branch was hard reset to remote state.",
                details=result,
            )
            background_tasks.add_task(connection_manager.broadcast_status_update)
            return GitCommandResponse(message=result.get("message"), details=result)
        except Exception as e:
            background_tasks.add_task(connection_manager.broadcast_status_update)
            handle_git_exception(e, action_name, service)


# --- Management & WebSocket Endpoints ---


@router.get("/activity-log", response_model=List[LogEntry], dependencies=auth_deps)
def get_git_activity_log():
    return get_all_logs()


@router.delete("/activity-log", status_code=204, dependencies=auth_deps)
def delete_git_activity_log():
    try:
        clear_all_logs()
        return Response(status_code=204)
    except Exception as e:
        logger.error(f"Failed to clear activity logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear logs.") from e


@router.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
