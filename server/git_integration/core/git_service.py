# server/git_integration/core/git_service.py
"""
This module defines the GitService class, which acts as the primary
business logic layer for the Git integration. It orchestrates operations
using the Repository (for reads) and Executor (for writes) classes to
fulfill high-level user workflows like 'sync' or 'resolve conflict'.
"""

from typing import Any, Dict, List, Optional

import pygit2
from pygit2 import GitError

from logger import logger

from .. import git_config
from .git_exceptions import GitManagerError, MergeConflictError, NoChangesError
from .git_executor import TEMP_NOTE_REF, Executor
from .git_repository import Repository


class GitService:
    """Orchestrates high-level Git workflows."""

    def __init__(self, repository: Repository, executor: Executor):
        """
        Initializes the GitService with its dependencies.

        Args:
            repository: An instance of the Repository class for read operations.
            executor: An instance of the Executor class for write operations.
        """
        self.repository = repository
        self.executor = executor
        self._sync_repository()

    def _sync_repository(self):
        """Make read operations use the executor's current repository object."""
        self.repository.repo = self.executor.repo

    # --- Proxied Read Operations ---

    def get_status(self) -> Dict[str, Any]:
        return self.repository.get_status()

    def get_commit_history(
        self, limit: int = 20, page: int = 1
    ) -> List[Dict[str, Any]]:
        return self.repository.get_commit_history(limit=limit, page=page)

    def get_files_in_commit(self, commit_hash: str) -> List[Dict[str, str]]:
        return self.repository.get_files_in_commit(commit_hash)

    def list_branches(self) -> Dict[str, Any]:
        return self.repository.list_branches()

    # --- Proxied Write Operations ---

    def add_all(self):
        self.executor.add_all()
        self._sync_repository()

    def unstage_all(self):
        self.executor.unstage_all()
        self._sync_repository()

    def add_file(self, filepath: str):
        self.executor.add_file(filepath)
        self._sync_repository()

    def unstage_file(self, filepath: str):
        self.executor.unstage_file(filepath)
        self._sync_repository()

    def discard_file(self, filepath: str):
        self.executor.discard_file(filepath)
        self._sync_repository()

    def discard_all(self):
        self.executor.discard_all()
        self._sync_repository()

    def commit(self, message: str) -> Dict[str, Any]:
        result = self.executor.commit(message)
        self._sync_repository()
        return result

    def fetch(self, remote_name: Optional[str] = None) -> str:
        output = self.executor.fetch(remote_name)
        self._sync_repository()
        return output

    def push(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        result = self.executor.push(remote_name, branch_name)
        self._sync_repository()
        return result

    def switch_branch(self, branch_name: str):
        self.executor.switch_branch(branch_name)
        self._sync_repository()

    def reset_to_remote(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ):
        result = self.executor.reset_to_remote(remote_name, branch_name)
        self._sync_repository()
        return result

    def checkout_file_from_commit(self, commit_hash: str, filepath: str):
        self.executor.checkout_file_from_commit(commit_hash, filepath)
        self._sync_repository()

    # --- Complex Workflows ---

    def pull(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pulls changes from a remote repository by explicitly running fetch and then rebase/merge.
        """
        # Enforce clean workspace principle for standalone pulls
        if self.repository.repo.status():
            raise GitManagerError(
                "Cannot pull with uncommitted changes. Please commit, stash, or discard them first."
            )

        remote_to_use = remote_name or self.executor.default_remote

        try:
            old_head_oid_str = str(self.repository.repo.head.target)
        except GitError:
            old_head_oid_str = None

        logger.info(f"Step 1/2: Fetching from remote '{remote_to_use}'...")
        fetch_output = self.fetch(remote_to_use)

        current_branch_name = branch_name or self.repository.get_current_branch()
        if not current_branch_name or current_branch_name.startswith("DETACHED"):
            raise GitManagerError("Cannot pull in a detached HEAD state.")

        _, behind = self.repository.get_ahead_behind()
        if behind == 0:
            logger.info("Local branch is already up-to-date. Nothing to pull.")
            return {
                "message": "Pull successful. Already up-to-date.",
                "stdout": fetch_output,
                "commits_received": 0,
                "files_updated": [],
            }

        logger.info(
            f"Step 2/2: Found {behind} new commit(s). Applying changes with strategy: {git_config.GIT_PULL_STRATEGY.value}"
        )

        upstream_ref_name = self.repository.repo.branches.local[
            current_branch_name
        ].upstream.name

        if git_config.GIT_PULL_STRATEGY == git_config.PullStrategy.REBASE:
            operation_command = ["rebase", upstream_ref_name]
        else:  # MERGE strategy
            operation_command = ["merge", upstream_ref_name]

        operation_output = self.executor._execute_git_command(operation_command)
        self.executor._reopen_repository()
        self._sync_repository()

        new_head_oid = self.repository.repo.head.target
        commits_received = 0
        files_updated = []
        if old_head_oid_str:
            old_head_oid = pygit2.Oid(hex=old_head_oid_str)
            if old_head_oid != new_head_oid:
                try:
                    ahead, _ = self.repository.repo.ahead_behind(
                        new_head_oid, old_head_oid
                    )
                    commits_received = ahead
                    diff = self.repository.repo.diff(
                        self.repository.repo.get(old_head_oid), new_head_oid
                    )
                    files_updated = self.repository._get_diff_metadata(diff)
                except (GitError, ValueError):
                    pass

        return {
            "message": "Pull successful.",
            "stdout": f"""Fetch output:
{fetch_output}

Operation output:
{operation_output}""",
            "commits_received": commits_received,
            "files_updated": files_updated,
        }

    def sync_workspace(
        self, commit_message: str, remote_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs the "Commit & Sync" operation with a safe, isolated, ref-based note mechanism.
        """
        results = {}
        self.executor._cleanup_temp_notes()

        # The `sync` command can operate on a dirty workspace.
        # It will create a temporary commit. The standalone `pull` command cannot.
        is_dirty = bool(self.repository.repo.status())

        if is_dirty:
            logger.info(
                "Sync started with a dirty workspace. A temporary commit will be created."
            )
            self.executor.add_all()
            try:
                commit_result = self.executor.commit(message=commit_message)
                temp_commit_oid = pygit2.Oid(hex=commit_result["hash"])

                self.executor.repo.create_note(
                    "flatnotes-temporary-commit",
                    self.executor.author,
                    self.executor.committer,
                    str(temp_commit_oid),
                    TEMP_NOTE_REF,
                    True,
                )
                logger.info(f"Attached temp note to commit {str(temp_commit_oid)[:7]}")
                results["commit"] = commit_result
            except NoChangesError:
                results["commit"] = {"message": "No meaningful changes to commit."}
        else:
            logger.info(
                "Sync started with a clean workspace. No temporary commit created."
            )
            results["commit"] = {
                "message": "Workspace is clean, proceeding directly to pull."
            }

        try:
            self.fetch(remote_name)
            _, behind = self.repository.get_ahead_behind()
            if behind > 0:
                logger.info(f"Local branch is {behind} commit(s) behind. Pulling.")
                # We can call pull directly here because we know the state is clean or committed.
                results["pull"] = self.pull(remote_name=remote_name)
            else:
                logger.info("Local branch is up-to-date. Skipping pull.")
                results["pull"] = {"message": "Already up-to-date. Pull skipped."}
            results["push"] = self.push(remote_name=remote_name)
            self.executor._cleanup_temp_notes()
            self._sync_repository()
            return results
        except MergeConflictError:
            logger.warning("Merge conflict detected. Temp note preserved for rollback.")
            raise
        except Exception:
            self.executor._cleanup_temp_notes()
            raise

    def resolve_conflict(self, action: str) -> Dict[str, Any]:
        """Continues or aborts a rebase/merge operation."""
        state = self.repository.get_repository_state()
        try:
            if action == "continue":
                if state == "REBASING_CONTINUE":
                    continue_output = self.executor.rebase_continue()
                    self.executor._reopen_repository()
                    self._sync_repository()
                    push_output = self.push()
                    return {
                        "message": "Rebase finished and pushed.",
                        "details": f"""Rebase: {continue_output}
Push: {push_output}""",
                    }
                elif state == "MERGING":
                    commit_result = self.executor.commit(message=None)
                    self._sync_repository()
                    push_result = self.push()
                    return {
                        "message": "Merge finalized and pushed.",
                        "commit": commit_result,
                        "push": push_result,
                    }
                else:
                    raise GitManagerError(
                        f"No conflict resolution to continue in state '{state}'."
                    )

            elif action == "abort":
                message = self._abort_conflict_resolution()
                return {"message": "Operation aborted successfully.", "stdout": message}

            else:
                raise ValueError(f"Invalid resolution action: {action}")
        finally:
            self.executor._cleanup_temp_notes()
            self._sync_repository()

    def _abort_conflict_resolution(self) -> str:
        """Private helper to handle the complex abort logic."""
        state = self.repository.get_repository_state()
        operation_name, abort_command = "unknown", None

        if state.startswith("REBASING"):
            operation_name, abort_command = "rebase", self.executor.rebase_abort
        elif state.startswith("MERGING"):
            operation_name, abort_command = "merge", self.executor.merge_abort

        if not abort_command:
            self.executor._cleanup_temp_notes()
            return "No operation to abort."

        try:
            abort_command()
            logger.info(f"Successfully aborted {operation_name} operation.")
            #  Fully reopen repository to clear internal state *after* abort.
            self.executor._reopen_repository()
            self._sync_repository()
        except GitManagerError as e:
            self.executor._cleanup_temp_notes()
            raise GitManagerError(
                f"Critical error: Failed to abort {operation_name}: {e}"
            )

        try:
            head_commit = self.repository.repo.head.peel()
            # Check if the commit we landed on has our temporary note
            self.repository.repo.lookup_note(str(head_commit.id), TEMP_NOTE_REF)

            logger.info(
                f"Found temp commit note on '{str(head_commit.id)[:7]}'. Undoing."
            )

            if not head_commit.parents:
                return f"The {operation_name} was aborted. The initial temp commit was left."

            # Now that the state is clean, this reset should succeed.
            self.repository.repo.reset(head_commit.parents[0].id, pygit2.GIT_RESET_SOFT)
            self.executor._reopen_repository()  # Reopen again after reset for good measure
            self._sync_repository()
            return f"The {operation_name} was aborted. The temp sync commit has been undone."
        except KeyError:
            # This is the normal case for a user's own commit.
            logger.info("No temp note found. History correctly preserved.")
            return (
                f"The {operation_name} was aborted. Your commit history is untouched."
            )
        except GitError as e:
            # This case handles unexpected errors during the post-abort check.
            logger.error(f"Error during post-abort inspection: {e}.")
            return f"The {operation_name} was aborted, but a post-check failed."
