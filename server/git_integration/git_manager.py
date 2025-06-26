# server/git_integration/git_manager.py
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pygit2
from pygit2 import GitError, IndexEntry, Signature
from pygit2.enums import FileStatus, RepositoryState, SortMode

from logger import logger

from . import git_config
from .git_config import PullStrategy

# --- Constants ---
TEMP_NOTE_REF = "refs/notes/flatnotes-sync"


# --- Custom Exceptions for Clearer Error Handling ---
class GitManagerError(Exception):
    """Base exception for the GitManager."""


class RepositoryInvalidError(GitManagerError):
    """Raised when the repository is not valid or accessible."""


class MergeConflictError(GitManagerError):
    """Raised when a pull/rebase operation results in a merge conflict."""

    pass


class PushRejectedError(GitManagerError):
    """Raised when a push is rejected by the remote (e.g., non-fast-forward)."""

    pass


class RemoteNotFoundError(GitManagerError):
    """Raised when the specified remote does not exist."""


class BranchNotFoundError(GitManagerError):
    """Raised when the specified branch does not exist."""


class NoChangesError(GitManagerError):
    """Raised when an operation expects changes but finds none."""


class GitManager:
    # region: REPOSITORY INITIALIZATION & MAINTENANCE
    def __init__(
        self,
        repo_path: str,
        default_branch: str,
        default_remote: str,
        pull_strategy: PullStrategy,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
    ):
        """Initializes the GitManager."""
        self.repo_path = repo_path
        self.default_branch = default_branch
        self.default_remote = default_remote
        self.pull_strategy = pull_strategy
        self.author = (
            Signature(user_name, user_email) if user_name and user_email else None
        )
        self.committer = self.author

        try:
            git_repo_path = pygit2.discover_repository(repo_path)
            if git_repo_path is None:
                if git_config.GIT_AUTO_INIT:
                    logger.info(f"Initializing a new Git repository at '{repo_path}'")
                    self.repo = pygit2.init_repository(
                        repo_path, initial_head=self.default_branch
                    )
                    if self.author:
                        config = self.repo.config
                        config.set_multivar("user.name", ".*", self.author.name)
                        config.set_multivar("user.email", ".*", self.author.email)
                else:
                    raise RepositoryInvalidError(
                        f"No Git repository found at or above '{repo_path}'. "
                        "To automatically create one, set FLATNOTES_GIT_AUTO_INIT=true."
                    )
            else:
                self.repo = pygit2.Repository(git_repo_path)

            self._enforce_gitignore_rule()

        except GitError as e:
            raise RepositoryInvalidError(
                f"Invalid or inaccessible repository at '{repo_path}': {e}"
            ) from e

        logger.info(f"GitManager initialized for repository at: {self.repo.path}")

    def _enforce_gitignore_rule(self):
        """Ensures that the .flatnotes/ directory is present in the .gitignore file."""
        gitignore_path = os.path.join(self.repo.workdir, ".gitignore")
        preferred_rule = ".flatnotes/"
        valid_rules = {".flatnotes", ".flatnotes/"}

        if not os.path.exists(gitignore_path):
            logger.info(
                f"No .gitignore found. Creating one to ignore '{preferred_rule}'."
            )
            with open(gitignore_path, "w") as f:
                f.write(f"# Flatnotes specific ignores\n{preferred_rule}\n")
        else:
            rule_exists = False
            full_content = ""
            with open(gitignore_path, "r") as f:
                lines = f.readlines()
                full_content = "".join(lines)
                for line in lines:
                    cleaned_line = line.strip()
                    if cleaned_line in valid_rules:
                        rule_exists = True
                        break

            if not rule_exists:
                logger.warning(
                    f"A rule to ignore '.flatnotes' was not found in .gitignore. "
                    f"Appending '{preferred_rule}' to prevent committing cache."
                )
                with open(gitignore_path, "a") as f:
                    if not full_content.endswith("\n"):
                        f.write("\n")
                    f.write(
                        f"\n# Added by Flatnotes to ignore its cache\n{preferred_rule}\n"
                    )

    def _refresh_repository_state(self):
        """Force-reloads critical pygit2 state caches after an external command."""
        try:
            self.repo.index.read()
            self.repo.head  # Accessing .head re-reads the reference from disk
            logger.debug("Pygit2 repository state cache refreshed.")
        except GitError as e:
            logger.warning(f"Non-critical state refresh failed: {e}")

    def _reopen_repository(self):
        """Fully reopens the repository object to ensure absolute state consistency."""
        try:
            git_repo_path = pygit2.discover_repository(self.repo_path)
            self.repo = pygit2.Repository(git_repo_path)
            logger.debug("Repository reopened after a major state-changing operation.")
        except GitError as e:
            raise RepositoryInvalidError(
                f"Failed to reopen repository at '{self.repo_path}': {e}"
            ) from e

    # endregion

    # region: TEMPORARY NOTE MANAGEMENT
    def _cleanup_temp_notes(self):
        """Safely and atomically removes the entire temporary note reference."""
        try:
            note_ref = self.repo.references.get(TEMP_NOTE_REF)
            if note_ref:
                note_ref.delete()
                logger.info(
                    f"Successfully cleaned up temporary note ref: '{TEMP_NOTE_REF}'"
                )
        except (KeyError, GitError) as e:
            logger.debug(
                f"Could not clean up note ref (it may not exist or an error occurred): {e}"
            )

    # endregion

    # region: GIT COMMAND EXECUTION (SUBPROCESS BRIDGE)
    def _execute_git_command(self, command: List[str]) -> str:
        """Runs a git command using subprocess, with centralized error handling."""
        env = os.environ.copy()
        env["GIT_EDITOR"] = "true"
        if self.author:
            env["GIT_AUTHOR_NAME"] = self.author.name
            env["GIT_AUTHOR_EMAIL"] = self.author.email
        if self.committer:
            env["GIT_COMMITTER_NAME"] = self.committer.name
            env["GIT_COMMITTER_EMAIL"] = self.committer.email

        try:
            process = subprocess.run(
                ["git"] + command,
                cwd=self.repo.workdir,
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            self._refresh_repository_state()
            return process.stdout

        except subprocess.CalledProcessError as e:
            output_lower = (e.stdout + e.stderr).lower()
            logger.error(
                f"Git command `{' '.join(command)}` failed.\n"
                f"STDOUT: {e.stdout}\n"
                f"STDERR: {e.stderr}"
            )

            if command[0] == "push" and (
                "non-fast-forward" in output_lower
                or "updates were rejected" in output_lower
            ):
                raise PushRejectedError(e.stderr or e.stdout)

            if (
                "automatic merge failed" in output_lower
                or "conflict" in output_lower
                or "unmerged paths" in output_lower
            ):
                raise MergeConflictError(e.stderr or e.stdout)

            raise GitManagerError(e.stderr or e.stdout)

    # endregion

    # region: STATE INSPECTION & QUERIES (PYGIT2)
    def get_repository_state(self) -> str:
        """Determines the repository's detailed state using pygit2."""
        try:
            state_value = (
                self.repo.state()
            )  # IMPORTANT: state is a method, not a property.
        except GitError as e:
            logger.error(f"Error getting repository state: {e}")
            return "ERROR"

        rebase_states = (
            RepositoryState.REBASE,
            RepositoryState.REBASE_INTERACTIVE,
            RepositoryState.REBASE_MERGE,
        )

        if state_value in rebase_states:
            return (
                "REBASING_CONFLICT"
                if self.get_conflicted_files()
                else "REBASING_CONTINUE"
            )
        if state_value == RepositoryState.MERGE:
            return "MERGING_CONFLICT" if self.get_conflicted_files() else "MERGING"
        if state_value == RepositoryState.NONE:
            return "CLEAN"

        try:
            return RepositoryState(state_value).name
        except ValueError:
            return "UNKNOWN"

    def get_conflicted_files(self) -> List[str]:
        """Gets a list of conflicted file paths using the pygit2 index."""
        conflicted_paths = set()
        try:
            self.repo.index.read()
            if self.repo.index.conflicts is None:
                return []
            for _, ours, theirs in self.repo.index.conflicts:
                if ours:
                    conflicted_paths.add(ours.path)
                elif theirs:
                    conflicted_paths.add(theirs.path)
        except (GitError, TypeError) as e:
            logger.error(f"Error reading conflicts from pygit2 index: {e}")
            return []
        return sorted(list(conflicted_paths))

    def get_status(self) -> Dict[str, Any]:
        """Gets the repository status, including file changes and branch sync state."""
        all_files = [
            {"path": filepath, **self._map_status_flags(flags), "original_path": None}
            for filepath, flags in self.repo.status().items()
            if flags != FileStatus.CURRENT and flags != FileStatus.IGNORED
        ]
        ahead, behind = self.get_ahead_behind()
        is_tracking_upstream = False
        if not self.repo.head_is_detached:
            try:
                local_branch = self.repo.branches.local.get(self.repo.head.shorthand)
                if local_branch:
                    is_tracking_upstream = local_branch.upstream is not None
            except (GitError, KeyError):
                pass
        return {
            "files": all_files,
            "current_branch": self.get_current_branch(),
            "commits_ahead": ahead,
            "commits_behind": behind,
            "is_tracking_upstream": is_tracking_upstream,
            "repository_state": self.get_repository_state(),
            "files_changed_count": len(all_files),
        }

    def get_ahead_behind(self) -> Tuple[int, int]:
        """Gets the number of commits the local branch is ahead/behind its upstream."""
        if self.repo.head_is_unborn or self.repo.head_is_detached:
            return 0, 0
        try:
            local_branch = self.repo.branches.local[self.repo.head.shorthand]
            if not local_branch.upstream:
                return 0, 0
            return self.repo.ahead_behind(
                local_branch.target, local_branch.upstream.target
            )
        except (GitError, KeyError):
            return 0, 0

    def get_current_branch(self) -> Optional[str]:
        """Gets the current branch name, or a detached HEAD indicator."""
        if self.repo.head_is_unborn:
            return self.default_branch
        if self.repo.head_is_detached:
            return f"DETACHED ({str(self.repo.head.target)[:7]})"
        return self.repo.head.shorthand

    def _map_status_flags(self, status_flags: FileStatus) -> Dict[str, str]:
        """Maps pygit2's bitmask status to a dict of status characters."""
        index_char, work_tree_char = " ", " "
        if status_flags & FileStatus.INDEX_NEW:
            index_char = "A"
        elif status_flags & FileStatus.INDEX_MODIFIED:
            index_char = "M"
        elif status_flags & FileStatus.INDEX_DELETED:
            index_char = "D"
        elif status_flags & FileStatus.INDEX_RENAMED:
            index_char = "R"
        if status_flags & FileStatus.WT_NEW:
            work_tree_char = "?"
        elif status_flags & FileStatus.WT_MODIFIED:
            work_tree_char = "M"
        elif status_flags & FileStatus.WT_DELETED:
            work_tree_char = "D"
        elif status_flags & FileStatus.WT_RENAMED:
            work_tree_char = "R"
        if status_flags & FileStatus.CONFLICTED:
            index_char, work_tree_char = "U", "U"
        if work_tree_char == "?":
            index_char = "?"
        return {"index_status": index_char, "work_tree_status": work_tree_char}

    def get_remote_url(self, remote_name: Optional[str] = None) -> Optional[str]:
        """Gets the URL of the specified remote."""
        try:
            return self.repo.remotes[remote_name or self.default_remote].url
        except (KeyError, GitError):
            return None

    def _format_remote_url_for_web(self, url: str) -> Optional[str]:
        if not url:
            return None
        if url.startswith("git@"):
            path = url.split("@", 1)[1].replace(":", "/", 1)
            base_url = f"https://{path}"
            return base_url.removesuffix(".git").removesuffix("/")
        if url.startswith(("http://", "https://")):
            return url.removesuffix(".git").removesuffix("/")
        logger.warning(f"Could not parse remote URL format: {url}")
        return None

    # endregion

    # region: FILE OPERATIONS (PYGIT2)
    def add_file(self, filepath: str):
        """Stages a single file."""
        if (self.repo.status().get(filepath) or 0) & FileStatus.WT_DELETED:
            self.repo.index.remove(filepath)
        else:
            self.repo.index.add(filepath)
        self.repo.index.write()

    def add_all(self):
        """Stages all changes."""
        self.repo.index.add_all()
        self.repo.index.write()

    def unstage_file(self, filepath: str):
        """Unstages a single file."""
        if self.repo.head_is_unborn:
            try:
                self.repo.index.remove(filepath)
            except KeyError:
                pass
        else:
            head_commit = self.repo.head.peel()
            try:
                tree_entry = head_commit.tree[filepath]
                self.repo.index.add(
                    IndexEntry(filepath, tree_entry.id, tree_entry.filemode)
                )
            except KeyError:
                self.repo.index.remove(filepath)
        self.repo.index.write()

    def unstage_all(self):
        """Unstages all files."""
        if self.repo.head_is_unborn:
            self.repo.index.clear()
        else:
            self.repo.index.read_tree(self.repo.head.peel(pygit2.Tree))
        self.repo.index.write()

    def discard_file(self, filepath: str):
        """Discards changes to a single file in the working directory."""
        if (self.repo.status().get(filepath) or 0) & FileStatus.WT_NEW:
            full_path = os.path.join(self.repo.workdir, filepath)
            if os.path.exists(full_path):
                os.remove(full_path)
        else:
            self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE, paths=[filepath])

    def discard_all(self):
        """Discards all changes in the working directory."""
        self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE)
        self._execute_git_command(["clean", "-fd"])

    # endregion

    # region: COMMIT MANAGEMENT (PYGIT2)
    def commit(self, message: Optional[str]) -> Dict[str, Any]:
        """Creates a commit and returns structured data about it."""
        if message is None:
            try:
                with open(os.path.join(self.repo.path, "MERGE_MSG")) as f:
                    message = f.read().strip()
            except FileNotFoundError:
                raise ValueError("Cannot finalize merge: MERGE_MSG not found.")

        if not message.strip():
            raise ValueError("Commit message cannot be empty.")

        try:
            if not self.repo.index.diff_to_tree(self.repo.head.peel().tree):
                raise NoChangesError("No changes staged for commit.")
        except GitError:
            if len(self.repo.index) == 0:
                raise NoChangesError("No changes staged for commit.")

        tree = self.repo.index.write_tree()
        parents = [] if self.repo.head_is_unborn else [self.repo.head.target]

        merge_head_path = os.path.join(self.repo.path, "MERGE_HEAD")
        if os.path.exists(merge_head_path):
            with open(merge_head_path) as f:
                merge_parent_oid = pygit2.Oid(hex=f.read().strip())
                if merge_parent_oid not in parents:
                    parents.append(merge_parent_oid)

        commit_oid = self.repo.create_commit(
            "HEAD", self.author, self.committer, message, tree, parents
        )
        self.repo.index.write()

        if os.path.exists(merge_head_path):
            os.remove(merge_head_path)
            merge_msg_path = os.path.join(self.repo.path, "MERGE_MSG")
            if os.path.exists(merge_msg_path):
                os.remove(merge_msg_path)
            merge_mode_path = os.path.join(self.repo.path, "MERGE_MODE")
            if os.path.exists(merge_mode_path):
                os.remove(merge_mode_path)

        new_commit = self.repo.get(commit_oid)
        files_changed = self._get_diff_metadata(self._get_commit_diff(new_commit))

        self._refresh_repository_state()

        return {
            "hash": str(commit_oid),
            "message": message,
            "files_changed": files_changed,
        }

    def _get_commit_diff(self, commit: pygit2.Commit) -> pygit2.Diff:
        """Helper to get the diff of a commit against its parent."""
        if not commit.parents:
            # This is the initial commit. Diff its tree against an empty tree.
            empty_tree_oid = self.repo.TreeBuilder().write()
            empty_tree = self.repo.get(empty_tree_oid)
            return empty_tree.diff_to_tree(commit.tree)
        else:
            # This is a regular commit. Diff against its first parent.
            parent = commit.parents[0]
            return self.repo.diff(parent, commit)

    def _get_diff_metadata(self, diff: pygit2.Diff) -> List[Dict[str, Any]]:
        """Helper to extract structured file metadata from a diff object."""
        diff.find_similar()
        files = []
        for patch in diff:
            delta = patch.delta
            status = delta.status_char()
            if status in ("R", "C"):
                files.append(
                    {
                        "status": status,
                        "old_path": delta.old_file.path,
                        "path": delta.new_file.path,
                    }
                )
            else:
                path = delta.new_file.path if status != "D" else delta.old_file.path
                files.append({"status": status, "path": path})
        return files

    # endregion

    # region: REMOTE SYNC WORKFLOWS
    def fetch_only(self) -> str:
        """
        Executes a 'git fetch' to update remote-tracking branches without
        merging or rebasing. This is a safe, read-only style operation
        used for background updates.
        """
        logger.info(f"Executing fetch for remote '{self.default_remote}'...")
        output = self._execute_git_command(["fetch", self.default_remote, "--prune"])
        self._reopen_repository()  # It's crucial to reload state after fetch
        return output

    def commit_and_sync(
        self, commit_message: str, remote_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs the "Commit & Sync" operation with a safe, isolated, ref-based note mechanism.
        """
        results = {}

        self._cleanup_temp_notes()

        if self.repo.status():
            logger.info(
                "Sync started with a dirty workspace. A temporary commit will be created."
            )
            self.add_all()
            try:
                commit_result = self.commit(message=commit_message)
                temp_commit_oid = pygit2.Oid(hex=commit_result["hash"])

                self.repo.create_note(
                    "flatnotes-temporary-commit",  # message
                    self.author,  # author
                    self.committer,  # committer
                    str(temp_commit_oid),  # annotated_id
                    TEMP_NOTE_REF,  # ref
                    True,  # force
                )
                logger.info(
                    f"Attached temporary note in ref '{TEMP_NOTE_REF}' to commit {str(temp_commit_oid)[:7]}"
                )
                results["commit"] = commit_result
            except NoChangesError:
                results["commit"] = {"message": "No meaningful changes to commit."}
        else:
            logger.info(
                "Sync started with a clean workspace. No temporary commit will be created."
            )
            results["commit"] = {
                "message": "Workspace is clean, proceeding directly to pull."
            }

        try:
            logger.info("Fetching remote updates before sync...")
            self._execute_git_command(["fetch", self.default_remote])
            self._reopen_repository()

            _, behind = self.get_ahead_behind()

            if behind > 0:
                logger.info(
                    f"Local branch is {behind} commit(s) behind remote. Pulling changes."
                )
                results["pull"] = self.pull_remote_changes(remote_name=remote_name)
            else:
                logger.info(
                    "Local branch is up-to-date or ahead of remote. Skipping pull."
                )
                results["pull"] = {"message": "Already up-to-date. Pull skipped."}

            results["push"] = self.push_local_changes(remote_name=remote_name)

            self._cleanup_temp_notes()
            return results
        except MergeConflictError:
            logger.warning(
                "Merge conflict detected. Temporary note (if any) is preserved for rollback."
            )
            raise
        except Exception:
            self._cleanup_temp_notes()
            raise

    def pull_remote_changes(
        self, remote_name: Optional[str] = None, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pulls changes from a remote repository by explicitly running fetch and then rebase/merge.
        This provides more control and avoids ambiguity that can cause 'pull' to fail after an abort.
        """
        remote_to_use = remote_name or self.default_remote

        # We need the HEAD before any operation to calculate the diff later.
        try:
            old_head_oid_str = str(self.repo.head.target)
        except GitError:
            old_head_oid_str = None

        # Step 1: Always fetch first. This is a safe, non-destructive operation.
        logger.info(f"Step 1/2: Fetching from remote '{remote_to_use}'...")
        fetch_output = self._execute_git_command(["fetch", remote_to_use, "--prune"])
        self._reopen_repository()  # Fetch updates remote refs, we must reopen.

        # Step 2: Determine the correct upstream branch for the rebase/merge.
        current_branch_name = branch or self.get_current_branch()
        if not current_branch_name or current_branch_name.startswith("DETACHED"):
            raise GitManagerError("Cannot pull in a detached HEAD state.")

        try:
            local_branch = self.repo.branches.local[current_branch_name]
            if not local_branch.upstream:
                raise GitManagerError(
                    f"Branch '{current_branch_name}' has no configured upstream to pull from."
                )
            upstream_ref_name = local_branch.upstream.name
        except (KeyError, GitError) as e:
            raise GitManagerError(
                f"Could not determine upstream for branch '{current_branch_name}': {e}"
            )

        # Check if we are already up to date before attempting rebase/merge
        _, behind = self.get_ahead_behind()
        if behind == 0:
            logger.info(
                "Local branch is already up-to-date with its remote counterpart. Nothing to pull."
            )
            return {
                "message": "Pull successful. Already up-to-date.",
                "stdout": fetch_output,
                "commits_received": 0,
                "files_updated": [],
            }

        logger.info(
            f"Step 2/2: Found {behind} new commit(s). Applying changes with strategy: {self.pull_strategy.value}"
        )

        # Step 3: Explicitly execute rebase or merge against the determined upstream.
        if self.pull_strategy == PullStrategy.REBASE:
            operation_command = ["rebase", upstream_ref_name]
        else:  # MERGE strategy
            operation_command = ["merge", upstream_ref_name]

        operation_output = self._execute_git_command(operation_command)

        # After a successful rebase/merge, reopen again to ensure all state is fresh.
        self._reopen_repository()

        # Step 4: Analyze the result for a rich response.
        new_head_oid = self.repo.head.target

        commits_received = 0
        files_updated = []
        if old_head_oid_str:
            old_head_oid = pygit2.Oid(hex=old_head_oid_str)
            if old_head_oid != new_head_oid:
                try:
                    # Use pygit2 to calculate the diff and commit count
                    ahead, _ = self.repo.ahead_behind(new_head_oid, old_head_oid)
                    commits_received = ahead
                    diff = self.repo.diff(self.repo.get(old_head_oid), new_head_oid)
                    files_updated = self._get_diff_metadata(diff)
                except (GitError, ValueError):
                    logger.warning(
                        "Could not calculate diff after pull, history may have been rewritten extensively."
                    )
                    pass

        return {
            "message": "Pull successful.",
            "stdout": f"Fetch output:\n{fetch_output}\n\nOperation output:\n{operation_output}",
            "commits_received": commits_received,
            "files_updated": files_updated,
        }

    def push_local_changes(
        self, remote_name: Optional[str] = None, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pushes local commits to a remote repository."""
        remote = remote_name or self.default_remote
        branch_to_push = branch or self.get_current_branch()
        if self.repo.head_is_detached or branch_to_push.startswith("DETACHED"):
            raise GitManagerError("Cannot push in a detached HEAD state.")

        ahead, _ = self.get_ahead_behind()
        if ahead == 0:
            return {"message": "Nothing to push."}

        commits_to_push, files_changed = [], []
        if ahead > 0:
            local_branch = self.repo.branches.local[self.repo.head.shorthand]
            if upstream_ref := local_branch.upstream:
                walker = self.repo.walk(local_branch.target, SortMode.TOPOLOGICAL)
                for i, commit in enumerate(walker):
                    if i >= ahead:
                        break
                    commits_to_push.append(
                        {"hash": str(commit.id), "message": commit.message.strip()}
                    )
                diff = self.repo.diff(upstream_ref.target, local_branch.target)
                files_changed = self._get_diff_metadata(diff)

        output = self._execute_git_command(["push", remote, branch_to_push])
        self._reopen_repository()
        return {
            "message": "Push successful.",
            "stdout": output,
            "commits_pushed": ahead,
            "commits": commits_to_push,
            "files_changed": files_changed,
        }

    # endregion

    # region: CONFLICT RESOLUTION
    def continue_conflict_resolution(self) -> Dict[str, Any]:
        """Continues a rebase or merge and cleans up any temporary notes."""
        try:
            state = self.get_repository_state()
            if state == "REBASING_CONTINUE":
                continue_output = self._execute_git_command(["rebase", "--continue"])
                push_output = self.push_local_changes()
                self._reopen_repository()
                return {
                    "message": "Rebase finished and pushed successfully.",
                    "details": f"Rebase: {continue_output}\nPush: {push_output}",
                }
            elif state == "MERGING":
                commit_result = self.commit(message=None)
                push_result = self.push_local_changes()
                self._reopen_repository()
                return {
                    "message": "Merge finalized and pushed successfully.",
                    "commit": commit_result,
                    "push": push_result,
                }
            else:
                raise GitManagerError(
                    f"No conflict resolution to continue in state '{state}'."
                )
        finally:
            self._cleanup_temp_notes()

    def abort_conflict_resolution(self) -> str:
        """
        Aborts the current conflict state, safely checking for a git note to identify and reset only temporary commits.
        """
        state = self.get_repository_state()
        operation_name, abort_command = "unknown operation", None

        if state.startswith("REBASING"):
            operation_name, abort_command = "rebase", ["rebase", "--abort"]
        elif state.startswith("MERGING"):
            operation_name, abort_command = "merge", ["merge", "--abort"]

        if not abort_command:
            return "No operation to abort."

        try:
            self._execute_git_command(abort_command)
            logger.info(f"Successfully aborted {operation_name} operation.")
        except GitManagerError as e:
            self._cleanup_temp_notes()
            raise GitManagerError(
                f"Critical error: Failed to abort {operation_name}: {e}"
            )

        self._reopen_repository()

        try:
            head_commit_after_abort = self.repo.head.peel()
            self.repo.lookup_note(str(head_commit_after_abort.id), TEMP_NOTE_REF)

            logger.info(
                f"Found temporary commit note on '{str(head_commit_after_abort.id)[:7]}'. Undoing this commit."
            )

            if not head_commit_after_abort.parents:
                self._cleanup_temp_notes()
                return f"The {operation_name} was aborted. The initial temporary commit was left in place."

            self.repo.reset(
                head_commit_after_abort.parents[0].id, pygit2.GIT_RESET_SOFT
            )
            self._reopen_repository()

            self._cleanup_temp_notes()
            return f"The {operation_name} was aborted. The temporary sync commit has been undone and your changes are now in the staging area."
        except KeyError:
            logger.info(
                "No temporary note found for HEAD. History correctly preserved."
            )
            self._cleanup_temp_notes()
            return (
                f"The {operation_name} was aborted. Your commit history is untouched."
            )
        except GitError as e:
            logger.error(
                f"Error during post-abort inspection: {e}. Cleaning up and exiting."
            )
            self._cleanup_temp_notes()
            return f"The {operation_name} was aborted, but a post-check failed. Please verify repository state."

    # endregion

    # region: HISTORY & INSPECTION
    def get_commit_history(
        self, limit: int = 20, page: int = 1
    ) -> List[Dict[str, Any]]:
        """Gets paginated commit history, attempting to fetch first."""
        if self.repo.head_is_unborn:
            return []
        try:
            self._execute_git_command(["fetch", self.default_remote, "--prune"])
        except GitManagerError:
            pass

        walker = self.repo.walk(self.repo.head.target, SortMode.TOPOLOGICAL)
        commits = list(walker)
        paginated_commits = commits[(page - 1) * limit : page * limit]
        upstream_commit_oid = None
        if not self.repo.head_is_detached:
            if local_branch := self.repo.branches.local.get(self.repo.head.shorthand):
                if local_branch.upstream:
                    upstream_commit_oid = local_branch.upstream.target
        log_entries = []
        for c in paginated_commits:
            is_pushed = False
            if upstream_commit_oid:
                if c.id == upstream_commit_oid or self.repo.descendant_of(
                    upstream_commit_oid, c.id
                ):
                    is_pushed = True
            log_entries.append(
                {
                    "hash": str(c.id),
                    "author_name": c.author.name,
                    "author_email": c.author.email,
                    "date": datetime.fromtimestamp(
                        c.author.time, tz=datetime.now().astimezone().tzinfo
                    ).isoformat(),
                    "message": c.message.strip(),
                    "is_pushed": is_pushed,
                }
            )
        return log_entries

    def get_files_in_commit(self, commit_hash: str) -> List[Dict[str, str]]:
        """Gets a list of files and their statuses within a specific commit."""
        commit = self.repo.get(commit_hash)
        if not isinstance(commit, pygit2.Commit):
            raise GitError(f"Object not found for hash '{commit_hash}'")
        return self._get_diff_metadata(self._get_commit_diff(commit))

    # endregion

    # region: BRANCH MANAGEMENT
    def list_branches(self) -> Dict[str, Any]:
        """Lists all local and remote branches after a fresh fetch."""
        try:
            self._execute_git_command(["fetch", self.default_remote, "--prune"])
        except GitManagerError:
            pass
        active_branch_name = self.get_current_branch()
        branches = []
        for name in self.repo.branches.local:
            branches.append(
                {
                    "name": name,
                    "is_active": name == active_branch_name,
                    "is_remote": False,
                }
            )
        for name in self.repo.branches.remote:
            if not name.endswith("/HEAD"):
                branch_part = name.split("/", 1)[1]
                branches.append(
                    {"name": branch_part, "is_active": False, "is_remote": True}
                )

        # Deduplicate and sort
        unique_branches = {(b["name"], b["is_remote"]): b for b in branches}.values()
        branches = sorted(
            list(unique_branches), key=lambda x: (x["is_remote"], x["name"])
        )
        return {"branches": branches, "current_branch": active_branch_name}

    def switch_branch(self, branch_name: str):
        """Switches to a different local or remote branch."""
        if self.get_repository_state() != "CLEAN":
            raise GitManagerError(
                f"Cannot switch branch while in '{self.get_repository_state()}' state."
            )
        if branch_name in self.repo.branches.local:
            self.repo.checkout(self.repo.branches.local[branch_name])
            return

        try:
            remote_branch_name = f"{self.default_remote}/{branch_name}"
            remote_branch = self.repo.branches.remote[remote_branch_name]
            local_branch = self.repo.create_branch(branch_name, remote_branch.peel())
            local_branch.upstream = remote_branch
            self.repo.checkout(local_branch)
        except KeyError:
            raise BranchNotFoundError(
                f"Branch '{branch_name}' not found locally or on remote '{self.default_remote}'."
            )

    def reset_to_remote(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ):
        """Hard resets the current branch to its upstream counterpart."""
        if self.repo.head_is_detached:
            raise GitManagerError("Cannot reset in detached HEAD state.")
        local_branch_name = branch_name or self.get_current_branch()
        local_branch = self.repo.branches.local[local_branch_name]
        if not local_branch.upstream:
            raise GitManagerError("Branch has no upstream to reset to.")

        self._execute_git_command(["fetch", remote_name or self.default_remote])
        upstream_commit = self.repo.lookup_reference(local_branch.upstream.name).peel()
        self.repo.reset(upstream_commit.id, pygit2.GIT_RESET_HARD)
        self._reopen_repository()
        return {"message": f"Reset branch '{local_branch_name}' to remote state."}

    def checkout_file_from_commit(self, commit_hash: str, filepath: str):
        """Restores a single file to its state from a specific commit."""
        commit = self.repo.get(commit_hash)
        if not isinstance(commit, pygit2.Commit):
            raise GitError(f"Hash '{commit_hash}' is not a commit.")
        if filepath not in commit.tree:
            raise KeyError(f"File '{filepath}' not found in commit '{commit_hash}'")
        self.repo.checkout_tree(
            treeish=commit.tree, paths=[filepath], strategy=pygit2.GIT_CHECKOUT_FORCE
        )

    # endregion
