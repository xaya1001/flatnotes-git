# server/git_integration/git_manager.py
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pygit2
from pygit2 import GitError, IndexEntry, Signature
from pygit2.enums import FileStatus, RepositoryState, SortMode

from logger import logger

from . import config as git_config


# --- Custom Exceptions for Clearer Error Handling ---
class GitManagerError(Exception):
    """Base exception for the GitManager."""


class RepositoryInvalidError(GitManagerError):
    """Raised when the repository is not valid or accessible."""


class MergeConflictError(GitManagerError):
    """Raised when a pull/rebase operation results in a merge conflict."""

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
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
    ):
        self.repo_path = repo_path
        self.default_branch = default_branch
        self.default_remote = default_remote
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

        except GitError as e:
            raise RepositoryInvalidError(
                f"Invalid or inaccessible repository at '{repo_path}': {e}"
            ) from e

        logger.info(f"GitManager initialized for repository at: {self.repo.path}")

    def _run_git_command(self, command: List[str]) -> str:
        """Runs a git command using subprocess, centralizing error handling."""
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
            logger.error(
                f"Git command `{' '.join(command)}` failed. stderr: {e.stderr}"
            )
            if "conflict" in e.stderr.lower() or "unmerged paths" in e.stderr.lower():
                raise MergeConflictError(e.stderr)
            raise GitManagerError(e.stderr)

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

    def get_repository_state(self) -> str:
        """
        Determines the repository state.
        """
        git_dir = self.repo.path

        if os.path.isdir(os.path.join(git_dir, "rebase-merge")) or os.path.isdir(
            os.path.join(git_dir, "rebase-apply")
        ):
            if self.get_conflicted_files():
                return "REBASING_CONFLICT"
            else:
                return "REBASING_CONTINUE"

        if os.path.exists(os.path.join(git_dir, "MERGE_HEAD")):
            # For now, we can keep MERGING simple, but it could be enhanced similarly.
            return "MERGING"

        return "CLEAN"

    def get_status(self) -> Dict[str, Any]:
        # This method now becomes the single source of truth for status.
        all_files = [
            {
                "path": filepath,
                **self._map_status_flags(flags),
                "original_path": None,
            }
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

    def commit(self, message: str) -> str:
        if not message.strip():
            raise ValueError("Commit message cannot be empty.")
        if not self.repo.status():
            raise NoChangesError("No changes to commit.")

        tree = self.repo.index.write_tree()
        if not self.repo.head_is_unborn:
            if self.repo.head.peel().tree.id == tree:
                raise NoChangesError("No changes staged for commit.")

        parents = [] if self.repo.head_is_unborn else [self.repo.head.target]
        commit_oid = self.repo.create_commit(
            "HEAD", self.author, self.committer, message, tree, parents
        )
        self.repo.index.write()
        return str(commit_oid)

    def pull_remote_changes(
        self,
        remote_name: Optional[str] = None,
        branch: Optional[str] = None,
        rebase: bool = False,
    ) -> Dict[str, Any]:
        remote = remote_name or self.default_remote
        branch_to_pull = branch or self.get_current_branch()
        if self.repo.head_is_detached or branch_to_pull.startswith("DETACHED"):
            raise GitManagerError("Cannot pull in a detached HEAD state.")

        command = ["pull", remote, branch_to_pull]
        if rebase:
            command.append("--rebase")

        output = self._run_git_command(command)
        return {"message": "Pull successful.", "stdout": output}

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

    def sync_workspace(
        self, commit_message: str, remote_name: Optional[str] = None
    ) -> Dict[str, Any]:
        results = {}
        if self.repo.status():
            self.add_all()
            try:
                commit_hash = self.commit(commit_message)
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
        results["pull"] = self.pull_remote_changes(remote_name=remote_name, rebase=True)
        results["push"] = {"message": self.push_local_changes(remote_name=remote_name)}
        return results

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

    def get_conflicted_files(self) -> List[str]:
        """The most reliable way to get conflicted files is by parsing porcelain status."""
        try:
            status_output = self._run_git_command(["status", "--porcelain"])
            conflicted = []
            for line in status_output.splitlines():
                if line.startswith("UU "):
                    conflicted.append(line[3:].strip())
            return conflicted
        except GitManagerError:
            return []

    def rebase_continue(self) -> Dict[str, Any]:
        if not self.get_repository_state().startswith("REBASING"):
            raise GitManagerError("No rebase in progress to continue.")
        if self.get_conflicted_files():
            raise GitManagerError("Cannot continue with unresolved conflicts.")

        continue_output = self._run_git_command(["rebase", "--continue"])

        push_output = self.push_local_changes()
        return {
            "message": "Rebase finished and pushed successfully.",
            "details": f"{continue_output}\n{push_output}",
        }

    def rebase_abort(self) -> str:
        if not self.get_repository_state().startswith("REBASING"):
            return "No rebase in progress to abort."
        return self._run_git_command(["rebase", "--abort"])
