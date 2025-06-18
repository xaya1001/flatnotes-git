# server/git_integration/git_models.py
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# --- Common Models ---
class GitCommandResponse(BaseModel):
    """Generic response for simple Git commands."""

    message: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    details: Optional[Any] = None  # For any additional structured data


# --- Status Endpoint ---
class GitFileStatusItem(BaseModel):
    """Represents the status of a single file in the Git repository."""

    path: str
    index_status: str  # Status in the index (e.g., 'A', 'M', 'D', 'R', 'C', ' ')
    work_tree_status: str  # Status in the working tree (e.g., 'M', 'D', '?', ' ')
    original_path: Optional[str] = None  # For renamed or copied files


class GitStatusResponse(BaseModel):
    """Response model for Git status."""

    files: List[GitFileStatusItem]
    current_branch: Optional[str]
    commits_ahead: int
    commits_behind: int
    is_tracking_upstream: bool
    repository_state: str
    files_changed_count: int


# --- Commit Endpoint ---
class GitCommitRequest(BaseModel):
    """Request model for committing changes."""

    message: str = Field(..., description="Commit message.", min_length=0)


# --- Log Endpoint ---
class GitLogEntry(BaseModel):
    """Represents a single entry in the Git commit log."""

    hash: str
    author_name: str
    author_email: str
    date: str  # ISO 8601 format string
    message: str
    is_pushed: bool = True


class GitLogResponse(BaseModel):
    """Response model for Git commit log."""

    log: List[GitLogEntry]
    page: int
    limit: int
    remote_base_url: Optional[str] = None


# --- Pull Endpoint (Query Parameters as a Model for clarity) ---
# These will be used as Depends() or directly in function signature for query params
class GitPullParams(BaseModel):
    remote: Optional[str] = None
    branch: Optional[str] = None
    rebase: bool = False
    autostash: bool = True


# --- Push Endpoint (Query Parameters as a Model for clarity) ---
class GitPushParams(BaseModel):
    remote: Optional[str] = None
    branch: Optional[str] = None
    force: bool = False


# --- Additional Info Endpoint (Example) ---
class GitRepositoryInfoResponse(BaseModel):
    """Provides general information about the Git repository setup for the frontend."""

    current_branch: Optional[str]
    configured_remote_name: str
    configured_remote_url: Optional[str]
    configured_default_branch: str
    git_enabled: bool
    repo_path_is_git_dir: bool  # Indicates if FLATNOTES_PATH is a valid .git repo


class GitFileOperationRequest(BaseModel):
    filepath: str = Field(..., description="The path of the file to operate on.")


class GitStatusSummaryResponse(BaseModel):
    current_branch: Optional[str]
    files_changed_count: int
    commits_ahead: int
    commits_behind: int
    is_tracking_upstream: bool
    repository_state: str


class BranchInfo(BaseModel):
    name: str
    is_active: bool
    is_remote: bool


class BranchListResponse(BaseModel):
    branches: List[BranchInfo]
    current_branch: Optional[str]


class SwitchBranchRequest(BaseModel):
    branch_name: str = Field(..., description="The name of the branch to switch to.")


class GitRestoreFileRequest(BaseModel):
    commit_hash: str = Field(..., description="The hash of the commit to restore from.")
    filepath: str = Field(..., description="The path of the file to restore.")
