from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import Optional

from auth.base import BaseAuth
from global_config import GlobalConfig
from logger import logger

from . import git_utils
from . import config as git_config 
from .exceptions import GitCommandError
from .git_models import (
    GitCommandResponse,
    GitStatusResponse,
    GitFileStatusItem, # For constructing response within router if needed
    GitCommitRequest,
    GitLogResponse,
    GitLogEntry,
    GitPullParams, # For Depends
    GitPushParams, # For Depends
    GitRepositoryInfoResponse,
    GitFileOperationRequest,
    GitStatusSummaryResponse
)
from .exceptions import GitCommandError

# Initialize dependencies for auth
# This needs to be done carefully as global_config instance is in main.py
# We can pass auth_deps from main.py when including the router,
# or re-initialize parts of it here if necessary.
# For simplicity and to adhere to the plan, we'll assume auth_deps is correctly imported/passed.
# One way to get auth_deps:
main_global_config = GlobalConfig()
auth: Optional[BaseAuth] = main_global_config.load_auth() # Potentially re-loads auth
auth_deps = [Depends(auth.authenticate)] if auth else []
# A better way might be to pass auth_deps when including the router in main.py,
# but let's proceed with this for now and refine if it causes issues.

router = APIRouter()

def check_git_enabled():
    """Dependency to check if Git integration is enabled."""
    if not git_config.GIT_ENABLED:
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail="Git integration is not enabled on the server."
        )
    # Additionally, check if the repo path is a valid git directory before most operations.
    # This is now also done inside execute_git_command, but an early check here is good.
    try:
        if not git_config.GIT_REPO_PATH or not git_utils.os.path.isdir(git_config.GIT_REPO_PATH):
             raise HTTPException(status_code=500, detail=f"Git repository path '{git_config.GIT_REPO_PATH}' is not configured or not a directory.")
        
        # Check if it's a .git directory (basic check)
        # More thorough check is inside execute_git_command
        # git_utils.execute_git_command(["rev-parse", "--is-inside-work-tree"], check=True)
    except GitCommandError as e:
        logger.error(f"Git repo check failed: {e.message} - {e.stderr}")
        raise HTTPException(status_code=500, detail=f"The configured notes directory is not a valid Git repository: {e.stderr or e.message}")


common_deps = auth_deps + [Depends(check_git_enabled)]

@router.get(
    "/status",
    response_model=GitStatusResponse,
    dependencies=common_deps,
    summary="Get Git Repository Status"
)
async def get_git_status():
    """Retrieves the status of the Git repository, including changed files and current branch."""
    try:
        status_data = git_utils.get_status() # This now returns a dict
        return GitStatusResponse(**status_data)
    except GitCommandError as e:
        logger.error(f"API Error getting Git status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected API Error getting Git status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching Git status.")

@router.post(
    "/add_all",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Stage All Changes"
)
async def add_all_git_changes():
    """Adds all new, modified, and deleted files to the Git staging area ('git add -A')."""
    try:
        stdout, stderr = git_utils.add_all_changes()
        return GitCommandResponse(message="All changes added to staging.", stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        logger.error(f"API Error adding all changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected API Error adding all changes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while staging changes.")

@router.post(
    "/commit",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Commit Staged Changes"
)
async def commit_git_changes(commit_request: GitCommitRequest = Body(...)):
    """Commits previously staged changes with the provided message."""
    try:
        stdout, stderr = git_utils.commit_changes(message=commit_request.message)
        if "No changes staged for commit" in stdout:
             return GitCommandResponse(message=stdout, stdout=stdout, stderr=stderr)
        return GitCommandResponse(message="Changes committed successfully.", stdout=stdout, stderr=stderr)
    except ValueError as e: # For empty commit message
        raise HTTPException(status_code=400, detail=str(e))
    except GitCommandError as e:
        logger.error(f"API Error committing changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected API Error committing changes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while committing changes.")

@router.post(
    "/pull",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Pull Remote Changes"
)
async def pull_git_changes(params: GitPullParams = Depends()):
    """
    Pulls changes from the remote repository.
    Uses configured defaults if specific remote/branch are not provided.
    """
    try:
        stdout, stderr = git_utils.pull_remote_changes(
            remote=params.remote,
            branch=params.branch,
            rebase=params.rebase,
            autostash=params.autostash
        )
        return GitCommandResponse(message="Pull operation completed.", stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        logger.error(f"API Error pulling changes: {e}")
        # Check for specific common non-fatal git pull messages
        if "Already up to date." in stdout or "Already up to date." in stderr:
             return GitCommandResponse(message="Repository is already up to date.", stdout=stdout, stderr=stderr)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected API Error pulling changes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while pulling changes.")


@router.post(
    "/push",
    response_model=GitCommandResponse,
    dependencies=common_deps,
    summary="Push Local Changes"
)
async def push_git_changes(params: GitPushParams = Depends()):
    """
    Pushes local commits to the remote repository.
    Uses configured defaults if specific remote/branch are not provided.
    """
    try:
        stdout, stderr = git_utils.push_local_changes(
            remote=params.remote,
            branch=params.branch,
            force=params.force
        )
        return GitCommandResponse(message="Push operation completed.", stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        logger.error(f"API Error pushing changes: {e}")
        # Check for specific common non-fatal git push messages
        if "Everything up-to-date" in stdout or "Everything up-to-date" in stderr:
             return GitCommandResponse(message="Everything is up-to-date. Nothing to push.", stdout=stdout, stderr=stderr)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected API Error pushing changes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while pushing changes.")

@router.get(
    "/log",
    response_model=GitLogResponse,
    dependencies=common_deps,
    summary="Get Commit Log"
)
async def get_git_log(
    limit: int = Query(10, ge=1, le=100, description="Number of log entries per page."),
    page: int = Query(1, ge=1, description="Page number for pagination.")
):
    """Retrieves the commit history of the Git repository with pagination."""
    try:
        log_entries_data = git_utils.get_commit_log(limit=limit, page=page)
        # Convert list of dicts to list of GitLogEntry model instances
        log_entries_models = [GitLogEntry(**entry) for entry in log_entries_data]
        return GitLogResponse(log=log_entries_models, page=page, limit=limit)
    except GitCommandError as e:
        logger.error(f"API Error getting Git log: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected API Error getting Git log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching Git log.")

@router.get(
    "/info",
    response_model=GitRepositoryInfoResponse,
    dependencies=auth_deps, # Git specific check_git_enabled is not strictly needed if GIT_ENABLED is false, this endpoint should reflect that.
    summary="Get Git Integration Info"
)
async def get_git_integration_info():
    """Provides information about the Git integration status and configuration."""
    is_repo_valid_git_dir = False
    if git_config.GIT_ENABLED and git_config.GIT_REPO_PATH and git_utils.os.path.isdir(git_config.GIT_REPO_PATH):
        try:
            # A lightweight check if it's a git repo
            stdout, _ = git_utils.execute_git_command(["rev-parse", "--is-inside-work-tree"], check=False)
            if stdout.strip() == "true":
                is_repo_valid_git_dir = True
        except GitCommandError: # Catches if git command fails (e.g. not a repo) or git not found
            is_repo_valid_git_dir = False
        except FileNotFoundError: # Git not installed
            is_repo_valid_git_dir = False


    current_branch = None
    remote_url = None
    if git_config.GIT_ENABLED and is_repo_valid_git_dir:
        try:
            current_branch = git_utils.get_current_branch()
            remote_url = git_utils.get_remote_url(git_config.GIT_REMOTE_NAME)
        except GitCommandError as e:
            logger.warning(f"Could not fetch full git info during /info endpoint: {e.message}")
        # FileNotFoundError will be caught by the outer check

    return GitRepositoryInfoResponse(
        current_branch=current_branch,
        configured_remote_name=git_config.GIT_REMOTE_NAME,
        configured_remote_url=remote_url,
        configured_default_branch=git_config.GIT_DEFAULT_BRANCH,
        git_enabled=git_config.GIT_ENABLED,
        repo_path_is_git_dir=is_repo_valid_git_dir
    )
@router.post("/stage_file", response_model=GitCommandResponse, dependencies=common_deps)
async def stage_file(request: GitFileOperationRequest):
    """Stages a single file."""
    try:
        stdout, stderr = git_utils.add_file(request.filepath)
        return GitCommandResponse(message=f"File '{request.filepath}' staged.", stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/unstage_file", response_model=GitCommandResponse, dependencies=common_deps)
async def unstage_file(request: GitFileOperationRequest):
    """Unstages a single file."""
    try:
        stdout, stderr = git_utils.unstage_file(request.filepath)
        return GitCommandResponse(message=f"File '{request.filepath}' unstaged.", stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/discard_file", response_model=GitCommandResponse, dependencies=common_deps)
async def discard_file(request: GitFileOperationRequest):
    """Discards changes for a single file."""
    try:
        stdout, stderr = git_utils.discard_file_changes(request.filepath)
        return GitCommandResponse(message=f"Changes for '{request.filepath}' discarded.", stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/discard_all", response_model=GitCommandResponse, dependencies=common_deps)
async def discard_all_changes():
    """Discards all unstaged changes."""
    try:
        stdout, stderr = git_utils.discard_all_changes()
        return GitCommandResponse(message="All unstaged changes have been discarded.", stdout=stdout, stderr=stderr)
    except GitCommandError as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get(
    "/status-summary",
    response_model=GitStatusSummaryResponse,
    dependencies=common_deps,
    summary="Get a lightweight Git status summary"
)
async def get_git_status_summary():
    """Retrieves a quick summary of Git status, like current branch and number of changes."""
    try:
        summary_data = git_utils.get_status_summary()
        return GitStatusSummaryResponse(**summary_data)
    except GitCommandError as e:
        logger.error(f"API Error getting Git status summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))