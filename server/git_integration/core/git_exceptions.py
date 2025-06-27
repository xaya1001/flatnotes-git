# server/git_integration/core/exceptions.py
"""
Custom exceptions for the Git integration feature to allow for clear,
granular error handling in the application layer.
"""


class GitManagerError(Exception):
    """Base exception for all git integration errors."""


class RepositoryInvalidError(GitManagerError):
    """Raised when the repository is not valid, not found, or inaccessible."""


class MergeConflictError(GitManagerError):
    """Raised when a pull/rebase operation results in a merge conflict."""


class PushRejectedError(GitManagerError):
    """Raised when a push is rejected by the remote (e.g., non-fast-forward)."""


class RemoteNotFoundError(GitManagerError):
    """Raised when the specified remote does not exist."""


class BranchNotFoundError(GitManagerError):
    """Raised when the specified branch does not exist."""


class NoChangesError(GitManagerError):
    """Raised when an operation expects changes (e.g., a commit) but finds none."""
