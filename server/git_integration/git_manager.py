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
    def __init__(
        self,
        repo_path: str,
        default_branch: str,
        default_remote: str,
        pull_strategy: PullStrategy,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
    ):
        """
        Initializes the GitManager and ensures the .flatnotes directory is ignored.
        """
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

            self._ensure_flatnotes_ignored()

        except GitError as e:
            raise RepositoryInvalidError(
                f"Invalid or inaccessible repository at '{repo_path}': {e}"
            ) from e

        logger.info(f"GitManager initialized for repository at: {self.repo.path}")

    def _ensure_flatnotes_ignored(self):
        """
        Ensures that the .flatnotes/ directory is present in the .gitignore file.
        This is a critical function to prevent the app's cache from being committed.
        """
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
                    # Check each line, ignoring comments and whitespace.
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

    def _run_git_command(self, command: List[str]) -> str:
        """
        Runs a git command using subprocess, centralizing error handling and
        intelligently detecting conflict scenarios.
        """
        env = os.environ.copy()
        env["GIT_EDITOR"] = "true"
        try:
            process = subprocess.run(
                ["git"] + command,
                cwd=self.repo.workdir,
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )
            return process.stdout

        except subprocess.CalledProcessError as e:
            # Combine stdout and stderr for a comprehensive search, as different
            # git commands report conflicts in different streams.
            output_lower = (e.stdout + e.stderr).lower()

            logger.error(
                f"Git command `{' '.join(command)}` failed.\n"
                f"STDOUT: {e.stdout}\n"
                f"STDERR: {e.stderr}"
            )

            # Check for push rejections first, as they are a specific failure case.
            if command[0] == "push" and (
                "non-fast-forward" in output_lower
                or "updates were rejected" in output_lower
            ):
                raise PushRejectedError(e.stderr or e.stdout)

            # Check for a broad set of conflict indicators.
            if (
                "automatic merge failed" in output_lower
                or "conflict" in output_lower
                or "unmerged paths" in output_lower
            ):
                # This is a conflict scenario.
                raise MergeConflictError(e.stderr or e.stdout)
            else:
                # This is a different kind of Git error.
                raise GitManagerError(e.stderr or e.stdout)

    def get_conflicted_files(self) -> List[str]:
        """
        Gets a list of conflicted file paths using the pygit2 index.
        This is reliable and avoids subprocess parsing.
        """
        conflicted_paths = set()
        try:
            # Re-read the index to ensure it's in sync with the repository state
            self.repo.index.read()
            if self.repo.index.conflicts is None:
                return []

            for ancestor, ours, theirs in self.repo.index.conflicts:
                if ours:
                    conflicted_paths.add(ours.path)
                elif theirs:
                    conflicted_paths.add(theirs.path)
        except (GitError, TypeError) as e:
            logger.error(f"Error reading conflicts from pygit2 index: {e}")
            return []
        return sorted(list(conflicted_paths))

    def get_repository_state(self) -> str:
        """
        Determines the repository's detailed state using pygit2's state method,
        with custom logic to differentiate our required sub-states.
        """
        try:
            state_value = self.repo.state()  # self.repo.state is a method!
        except GitError as e:
            logger.error(f"Error getting repository state: {e}")
            return "ERROR"  # Return a generic error state

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
            # Fallback for other known states
            return RepositoryState(state_value).name
        except ValueError:
            logger.error(f"Pygit2 returned an unknown state value: {state_value}")
            return "UNKNOWN"

    def pull_remote_changes(
        self, remote_name: Optional[str] = None, branch: Optional[str] = None
    ) -> Dict[str, Any]:
        remote = remote_name or self.default_remote
        branch_to_pull = branch or self.get_current_branch()
        if self.repo.head_is_detached or branch_to_pull.startswith("DETACHED"):
            raise GitManagerError("Cannot pull in a detached HEAD state.")

        command = ["pull", remote, branch_to_pull]
        if self.pull_strategy == PullStrategy.REBASE:
            command.append("--rebase")

        output = self._run_git_command(command)
        return {"message": "Pull successful.", "stdout": output}

    def sync_workspace(
        self, commit_message: str, remote_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Performs the full "Commit & Sync" operation: add, commit, pull, push.
        """
        results = {}
        # The responsibility for checking for changes is now entirely within the commit() method.
        # This simplifies the logic here.
        if self.repo.status():
            self.add_all()
            try:
                commit_hash = self.commit(message=commit_message)
                results["commit"] = {
                    "hash": commit_hash,
                    "message": "Changes committed.",
                }
            except NoChangesError:
                results["commit"] = {
                    "hash": "no_changes",
                    "message": "No changes to commit.",
                }
        else:
            results["commit"] = {"hash": "no_changes", "message": "No local changes."}

        # The pull operation is the one that can raise MergeConflictError
        results["pull"] = self.pull_remote_changes(remote_name=remote_name)
        results["push"] = {"message": self.push_local_changes(remote_name=remote_name)}
        return results

    def continue_conflict_resolution(self) -> Dict[str, Any]:
        """Unified function to continue a conflict resolution process."""
        state = self.get_repository_state()
        if state == "REBASING_CONTINUE":
            # This is a rebase, so we use 'rebase --continue'
            continue_output = self._run_git_command(["rebase", "--continue"])
            push_output = self.push_local_changes()
            return {
                "message": "Rebase finished and pushed successfully.",
                "details": f"Rebase: {continue_output}\nPush: {push_output}",
            }
        elif state == "MERGING":
            # This is a merge. The "continue" action is to make a commit.
            # We will use the default merge message prepared by Git.
            commit_hash = self.commit(message=None)  # Let pygit2 use MERGE_MSG
            push_output = self.push_local_changes()
            return {
                "message": "Merge finalized and pushed successfully.",
                "details": f"Merge Commit: {commit_hash}\nPush: {push_output}",
            }
        else:
            raise GitManagerError(
                f"No conflict resolution to continue in state '{state}'."
            )

    def abort_conflict_resolution(self) -> str:
        """
        Aborts the current conflict state (rebase or merge) AND safely attempts
        to soft-reset the last-made "sync" commit, returning its changes to the
        staging area.
        """
        state = self.get_repository_state()
        operation_name = "unknown operation"

        # Step 1: Abort the Git operation (rebase or merge) using subprocess
        abort_command = None
        if state.startswith("REBASING"):
            operation_name = "rebase"
            abort_command = ["rebase", "--abort"]
        elif state.startswith("MERGING"):
            operation_name = "merge"
            abort_command = ["merge", "--abort"]

        if abort_command:
            try:
                self._run_git_command(abort_command)
                logger.info(f"Successfully aborted {operation_name} operation.")
            except GitManagerError as e:
                # If the primary abort command fails, this is a critical failure.
                raise GitManagerError(
                    f"Failed to abort the {operation_name} operation: {e}"
                )

        # At this point, the conflict state should be cleared.

        # Step 2: Safely attempt to soft reset the last commit, also using subprocess for consistency.
        try:
            head_commit = self.repo.head.peel()

            if not head_commit.parents:
                # This was the initial commit. We cannot reset it.
                logger.warning(
                    f"Conflict abort successful, but the last commit was the initial commit and cannot be reset."
                )
                return (
                    f"The {operation_name} was aborted, but the initial commit was left in place. "
                    "Your files are safe in that commit."
                )

            # Use subprocess for the reset to avoid pygit2 state issues.
            self._run_git_command(["reset", "--soft", "HEAD~1"])

            success_message = (
                f"The {operation_name} was successfully aborted. "
                "The last sync commit has been undone and your changes have been returned to the staging area."
            )
            logger.info(success_message)
            return success_message

        except GitManagerError as e:
            # This catches failure from the `git reset` command.
            # This is a partial failure, but we must report it as an error.
            error_message = (
                f"The {operation_name} was aborted, but an error occurred while trying to undo the last commit: {e}. "
                "Please check your repository's state manually."
            )
            logger.error(error_message)
            # Raise an exception so the router returns a non-200 status code.
            raise GitManagerError(error_message)
        except GitError as e:
            # This catches pygit2 errors (e.g., peeling HEAD).
            error_message = f"Failed to inspect repository for reset after abort: {e}"
            logger.error(error_message)
            raise GitManagerError(error_message)

    def commit(self, message: Optional[str]) -> str:
        """
        Creates a commit. If message is None, it attempts to use a default
        message from .git/MERGE_MSG for merge commits.
        """
        if message is None:
            # This is for finalizing a merge commit
            try:
                with open(os.path.join(self.repo.path, "MERGE_MSG")) as f:
                    message = f.read().strip()
            except FileNotFoundError:
                raise ValueError("Cannot finalize merge: MERGE_MSG not found.")

        if not message.strip():
            raise ValueError("Commit message cannot be empty.")

        try:
            # This works for all subsequent commits after the first one.
            head_tree = self.repo.head.peel().tree
            diff = self.repo.index.diff_to_tree(head_tree)
            # An empty diff object evaluates to False. This is the correct way to check.
            if not diff:
                raise NoChangesError("No changes staged for commit.")
        except GitError:
            # This handles the "unborn head" case (the very first commit).
            # If there's no HEAD, we simply check if the index is empty.
            if len(self.repo.index) == 0:
                raise NoChangesError("No changes staged for commit.")
        # --- END OF CORRECTION ---

        tree = self.repo.index.write_tree()
        parents = [] if self.repo.head_is_unborn else [self.repo.head.target]

        merge_head_path = os.path.join(self.repo.path, "MERGE_HEAD")
        if os.path.exists(merge_head_path):
            with open(merge_head_path) as f:
                merge_parent_oid = pygit2.Oid(hex=f.read().strip())
                # Avoid adding the same parent twice
                if merge_parent_oid not in parents:
                    parents.append(merge_parent_oid)

        commit_oid = self.repo.create_commit(
            "HEAD", self.author, self.committer, message, tree, parents
        )
        self.repo.index.write()

        if os.path.exists(merge_head_path):
            os.remove(merge_head_path)

        return str(commit_oid)

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

    def _map_status_flags(self, status_flags: FileStatus) -> Dict[str, str]:
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

    def get_ahead_behind(self) -> Tuple[int, int]:
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

    def get_status(self) -> Dict[str, Any]:
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

    def add_file(self, filepath: str):
        if (self.repo.status().get(filepath) or 0) & FileStatus.WT_DELETED:
            self.repo.index.remove(filepath)
        else:
            self.repo.index.add(filepath)
        self.repo.index.write()

    def add_all(self):
        self.repo.index.add_all()
        self.repo.index.write()

    def unstage_file(self, filepath: str):
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
        if self.repo.head_is_unborn:
            self.repo.index.clear()
        else:
            self.repo.index.read_tree(self.repo.head.peel(pygit2.Tree))
        self.repo.index.write()

    def discard_file(self, filepath: str):
        if (self.repo.status().get(filepath) or 0) & FileStatus.WT_NEW:
            full_path = os.path.join(self.repo.workdir, filepath)
            if os.path.exists(full_path):
                os.remove(full_path)
        else:
            self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE, paths=[filepath])

    def discard_all(self):
        self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE)
        self._run_git_command(["clean", "-fd"])

    def push_local_changes(
        self,
        remote_name: Optional[str] = None,
        branch: Optional[str] = None,
        force: bool = False,
    ) -> str:
        remote = remote_name or self.default_remote
        branch_to_push = branch or self.get_current_branch()
        if self.repo.head_is_detached or branch_to_push.startswith("DETACHED"):
            raise GitManagerError("Cannot push in a detached HEAD state.")
        command = ["push", remote, branch_to_push]
        if force:
            command.append("--force")
        return self._run_git_command(command)

    def get_commit_log(self, limit: int = 20, page: int = 1) -> List[Dict[str, Any]]:
        if self.repo.head_is_unborn:
            return []
        try:
            self._run_git_command(["fetch", self.default_remote, "--prune"])
        except GitManagerError:
            pass
        walker = self.repo.walk(self.repo.head.target, SortMode.TOPOLOGICAL)
        commits = list(walker)
        paginated_commits = commits[(page - 1) * limit : page * limit]
        upstream_commit_oid = None
        if not self.repo.head_is_detached:
            local_branch = self.repo.branches.local.get(self.repo.head.shorthand)
            if local_branch and local_branch.upstream:
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
        commit = self.repo.get(commit_hash)
        parent_tree = commit.parents[0].tree if commit.parents else None
        diff = self.repo.diff(parent_tree, commit.tree)
        return [
            {"status": d.delta.status_char(), "path": d.delta.new_file.path}
            for d in diff
        ]

    def get_remote_url(self, remote_name: Optional[str] = None) -> Optional[str]:
        try:
            return self.repo.remotes[remote_name or self.default_remote].url
        except (KeyError, GitError):
            return None

    def get_current_branch(self) -> Optional[str]:
        if self.repo.head_is_unborn:
            return self.default_branch
        if self.repo.head_is_detached:
            return f"DETACHED ({str(self.repo.head.target)[:7]})"
        return self.repo.head.shorthand

    def fetch_and_list_branches(self) -> Dict[str, Any]:
        try:
            self._run_git_command(["fetch", self.default_remote, "--prune"])
        except GitManagerError:
            pass
        return self.list_branches()

    def list_branches(self) -> Dict[str, Any]:
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
            branch_part = name.split("/", 1)[1]
            if branch_part not in self.repo.branches.local:
                branches.append(
                    {"name": branch_part, "is_active": False, "is_remote": True}
                )
        branches.sort(key=lambda x: (x["is_remote"], x["name"]))
        return {"branches": branches, "current_branch": active_branch_name}

    def switch_branch(self, branch_name: str):
        if self.get_repository_state() != "CLEAN":
            raise GitManagerError(
                f"Cannot switch branch while in '{self.get_repository_state()}' state."
            )
        if branch_name in self.repo.branches.local:
            self.repo.checkout(self.repo.branches.local[branch_name])
        else:
            remote_branch = self.repo.branches.remote[
                f"{self.default_remote}/{branch_name}"
            ]
            local_branch = self.repo.create_branch(branch_name, remote_branch.peel())
            local_branch.upstream = remote_branch
            self.repo.checkout(local_branch)

    def checkout_file_from_commit(self, commit_hash: str, filepath: str):
        commit = self.repo.get(commit_hash)
        if not isinstance(commit, pygit2.Commit):
            raise GitError(f"Hash '{commit_hash}' is not a commit.")
        self.repo.checkout_tree(
            treeish=commit.tree, paths=[filepath], strategy=pygit2.GIT_CHECKOUT_FORCE
        )

    def reset_to_remote(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ):
        if self.repo.head_is_detached:
            raise GitManagerError("Cannot reset in detached HEAD state.")
        local_branch_name = branch_name or self.get_current_branch()
        local_branch = self.repo.branches.local[local_branch_name]
        if not local_branch.upstream:
            raise GitManagerError("Branch has no upstream to reset to.")
        self._run_git_command(["fetch", remote_name or self.default_remote])
        upstream_commit = self.repo.lookup_reference(local_branch.upstream.name).peel()
        self.repo.reset(upstream_commit.id, pygit2.GIT_RESET_HARD)
        return {"message": f"Reset branch '{local_branch_name}' to remote state."}
