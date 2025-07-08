# server/git_integration/core/git_executor.py
import os
import subprocess
from typing import Any, Dict, List, Optional

import pygit2
from pygit2 import GitError, IndexEntry, Signature
from pygit2.enums import RepositoryOpenFlag, SortMode

from logger import logger

from .. import git_config
from .git_exceptions import (
    BranchNotFoundError,
    GitAuthenticationError,
    GitManagerError,
    MergeConflictError,
    NoChangesError,
    PushRejectedError,
    RepositoryInvalidError,
)

TEMP_NOTE_REF = "refs/notes/flatnotes-sync"


class Executor:
    """A class to execute state-changing Git operations."""

    def __init__(
        self,
        repo_path: str,
        default_branch: str,
        default_remote: str,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
    ):
        """Initializes the Executor."""
        self.repo_path = repo_path
        self.default_branch = default_branch
        self.default_remote = default_remote
        self.author = (
            Signature(user_name, user_email) if user_name and user_email else None
        )
        self.committer = self.author

        try:
            try:
                self.repo = pygit2.Repository(
                    repo_path, flags=RepositoryOpenFlag.NO_SEARCH
                )
                logger.info(f"Found existing Git repository at: {repo_path}")
            except GitError:
                if git_config.GIT_AUTO_INIT:
                    logger.info(f"Initializing a new Git repository at '{repo_path}'")
                    self.repo = pygit2.init_repository(
                        repo_path, initial_head=self.default_branch
                    )
                    logger.info(
                        f"Successfully initialized new Git repository at: {repo_path}"
                    )
                else:
                    raise RepositoryInvalidError(
                        f"No Git repository found at '{repo_path}'. "
                        "To automatically create one, set FLATNOTES_GIT_AUTO_INIT=true."
                    )

            # Set user info at repo level if provided, for subprocess commands
            if self.author:
                config = self.repo.config
                config.set_multivar("user.name", ".*", self.author.name)
                config.set_multivar("user.email", ".*", self.author.email)

            self._enforce_gitignore_rule()

        except GitError as e:
            raise RepositoryInvalidError(
                f"Invalid or inaccessible repository at '{repo_path}': {e}"
            ) from e

        logger.info(f"Git Executor initialized for repository at: {self.repo.path}")

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
                f.write(
                    f"""# Flatnotes specific ignores
{preferred_rule}
"""
                )
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
                        f"""\n# Added by Flatnotes to ignore its cache
{preferred_rule}
"""
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

    def _execute_git_command(self, command: List[str]) -> str:
        """
        Runs a git command using subprocess, with centralized error handling.
        Security Note: All elements in the 'command' list are constructed
        internally by the server and are not sourced from direct user input,
        mitigating command injection risks.
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
            self._refresh_repository_state()
            return process.stdout

        except subprocess.CalledProcessError as e:
            output_lower = (e.stdout + e.stderr).lower()
            logger.error(
                f"""Git command `{' '.join(command)}` failed.
STDOUT: {e.stdout}
STDERR: {e.stderr}"""
            )

            auth_error_patterns = [
                "could not read username",
                "permission denied (publickey)",
                "authentication failed",
                "fatal: repository not found",
            ]
            if any(p in output_lower for p in auth_error_patterns):
                raise GitAuthenticationError(e.stderr or e.stdout) from e

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

    def add_file(self, filepath: str):
        """Stages a single file."""
        if (self.repo.status().get(filepath) or 0) & pygit2.enums.FileStatus.WT_DELETED:
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
        if (self.repo.status().get(filepath) or 0) & pygit2.enums.FileStatus.WT_NEW:
            full_path = os.path.join(self.repo.workdir, filepath)
            if os.path.exists(full_path):
                os.remove(full_path)
        else:
            self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE, paths=[filepath])

    def discard_all(self):
        """Discards all changes in the working directory."""
        self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE)
        self._execute_git_command(["clean", "-fd"])

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

    def fetch(self, remote_name: Optional[str] = None) -> str:
        """Executes a 'git fetch' to update remote-tracking branches."""
        remote_to_use = remote_name or self.default_remote
        logger.info(f"Executing fetch for remote '{remote_to_use}'...")
        output = self._execute_git_command(["fetch", remote_to_use, "--prune"])
        self._reopen_repository()
        return output

    def push(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pushes local commits to a remote repository."""
        remote = remote_name or self.default_remote
        branch_to_push = branch_name or self.repo.head.shorthand
        if self.repo.head_is_detached or branch_to_push.startswith("DETACHED"):
            raise GitManagerError("Cannot push in a detached HEAD state.")

        local_branch = self.repo.branches.local[branch_to_push]
        if not local_branch.upstream:
            return {"message": "Nothing to push. Branch has no upstream."}

        ahead, _ = self.repo.ahead_behind(
            self.repo.head.target, local_branch.upstream.target
        )
        if ahead == 0:
            return {"message": "Nothing to push."}

        commits_to_push, files_changed = [], []
        if ahead > 0:
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

    def rebase_continue(self) -> str:
        """Continues an in-progress rebase."""
        return self._execute_git_command(["rebase", "--continue"])

    def rebase_abort(self) -> str:
        """Aborts an in-progress rebase."""
        return self._execute_git_command(["rebase", "--abort"])

    def merge_abort(self) -> str:
        """Aborts an in-progress merge."""
        return self._execute_git_command(["merge", "--abort"])

    def reset_to_remote(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ):
        """Hard resets the current branch to its upstream counterpart."""
        if self.repo.head_is_detached:
            raise GitManagerError("Cannot reset in detached HEAD state.")
        local_branch_name = branch_name or self.repo.head.shorthand
        local_branch = self.repo.branches.local[local_branch_name]
        if not local_branch.upstream:
            raise GitManagerError("Branch has no upstream to reset to.")

        self._execute_git_command(["fetch", remote_name or self.default_remote])
        upstream_commit = self.repo.lookup_reference(local_branch.upstream.name).peel()
        self.repo.reset(upstream_commit.id, pygit2.GIT_RESET_HARD)
        self._reopen_repository()
        return {"message": f"Reset branch '{local_branch_name}' to remote state."}

    def switch_branch(self, branch_name: str):
        """Switches to a different local or remote branch."""
        if self.repo.status():
            raise GitManagerError(
                "Cannot switch branch with uncommitted changes. Please commit or stash them first."
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

    def checkout_file_from_commit(self, commit_hash: str, filepath: str):
        """
        Restores a single file to its state from a specific commit.
        This is now smarter to handle restores of deleted files.
        """
        commit = self.repo.get(commit_hash)
        if not isinstance(commit, pygit2.Commit):
            raise GitError(f"Hash '{commit_hash}' is not a valid commit.")

        tree_to_checkout_from = None
        # Case 1: File exists in the target commit (add, modify)
        if filepath in commit.tree:
            tree_to_checkout_from = commit.tree
        # Case 2: File does NOT exist, check parent (likely a deletion)
        elif commit.parents:
            parent_commit = commit.parents[0]
            if filepath in parent_commit.tree:
                tree_to_checkout_from = parent_commit.tree

        if tree_to_checkout_from:
            self.repo.checkout_tree(
                treeish=tree_to_checkout_from,
                paths=[filepath],
                strategy=pygit2.GIT_CHECKOUT_FORCE,
            )
        else:
            # If not found in current or parent, then it's a true error
            raise KeyError(
                f"File '{filepath}' not found in commit '{commit_hash}' or its direct parent."
            )

    # Helper methods used by commit, copied from Repository for simplicity, could be refactored
    def _get_commit_diff(self, commit: pygit2.Commit) -> pygit2.Diff:
        if not commit.parents:
            empty_tree_oid = self.repo.TreeBuilder().write()
            empty_tree = self.repo.get(empty_tree_oid)
            return empty_tree.diff_to_tree(commit.tree)
        else:
            parent = commit.parents[0]
            return self.repo.diff(parent, commit)

    def _get_diff_metadata(self, diff: pygit2.Diff) -> List[Dict[str, Any]]:
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
