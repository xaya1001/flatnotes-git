# server/git_integration/git_models.py
import re
from pathlib import PurePosixPath
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
INVALID_BRANCH_CHARS_RE = re.compile(r"[\000-\037\177 ~^:?*\\[]")


def validate_repo_filepath(filepath: str) -> str:
    if not filepath or not filepath.strip():
        raise ValueError("File path cannot be empty.")
    if "\x00" in filepath:
        raise ValueError("File path cannot contain NUL bytes.")
    if "\\" in filepath:
        raise ValueError("File path must use POSIX separators.")
    path = PurePosixPath(filepath)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("File path must stay within the notes repository.")
    return filepath


def validate_branch_name(branch_name: str) -> str:
    if not branch_name or not branch_name.strip():
        raise ValueError("Branch name cannot be empty.")
    branch_parts = branch_name.split("/")
    if (
        branch_name.startswith(("/", "."))
        or branch_name.endswith(("/", ".", ".lock"))
        or "//" in branch_name
        or ".." in branch_name
        or "@{" in branch_name
        or branch_name == "@"
        or any(part.startswith(".") or part.endswith(".lock") for part in branch_parts)
        or INVALID_BRANCH_CHARS_RE.search(branch_name)
    ):
        raise ValueError("Branch name is not a valid Git branch name.")
    return branch_name


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

    @field_validator("filepath")
    @classmethod
    def filepath_must_stay_in_repo(cls, value: str) -> str:
        return validate_repo_filepath(value)


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

    @field_validator("branch_name")
    @classmethod
    def branch_name_must_be_valid(cls, value: str) -> str:
        return validate_branch_name(value)


class GitRestoreFileRequest(BaseModel):
    commit_hash: str = Field(..., description="The hash of the commit to restore from.")
    filepath: str = Field(..., description="The path of the file to restore.")

    @field_validator("commit_hash")
    @classmethod
    def commit_hash_must_be_hex(cls, value: str) -> str:
        if not COMMIT_HASH_RE.match(value):
            raise ValueError("Commit hash must be a 7-40 character hexadecimal value.")
        return value

    @field_validator("filepath")
    @classmethod
    def filepath_must_stay_in_repo(cls, value: str) -> str:
        return validate_repo_filepath(value)


class GitConfirmRequest(BaseModel):
    confirm: bool = Field(
        False, description="Must be true for destructive Git operations."
    )
