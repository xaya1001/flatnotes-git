# server/git_integration/core/git_repository.py
"""
This module defines the Repository class, which is responsible for all
read-only operations and state inspections of the Git repository.
It uses pygit2 for efficient, direct access to the repository data.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pygit2
from pygit2 import GitError
from pygit2.enums import FileStatus, RepositoryState, SortMode

from logger import logger

from .exceptions import RepositoryInvalidError


class Repository:
    """A read-only interface to query the state of the Git repository."""

    def __init__(self, repo_path: str, default_branch: str, default_remote: str):
        """
        Initializes the Repository reader.

        Args:
            repo_path: The file system path to the Git repository.
            default_branch: The default branch name (e.g., 'main').
            default_remote: The default remote name (e.g., 'origin').
        """
        self.repo_path = repo_path
        self.default_branch = default_branch
        self.default_remote = default_remote
        try:
            git_repo_path = pygit2.discover_repository(repo_path)
            if git_repo_path is None:
                # The decision to auto-init is handled by the Executor.
                # The Repository reader assumes a valid repo exists.
                raise RepositoryInvalidError(
                    f"No Git repository found at or above '{repo_path}'."
                )
            self.repo = pygit2.Repository(git_repo_path)
            logger.info(f"Repository reader initialized for repo at: {self.repo.path}")
        except GitError as e:
            raise RepositoryInvalidError(
                f"Invalid or inaccessible repository at '{repo_path}': {e}"
            ) from e

    def get_repository_state(self) -> str:
        """Determines the repository's detailed state using pygit2."""
        try:
            # IMPORTANT!!!: .state is a method, not a property.
            state_value = self.repo.state()
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

    def get_commit_history(
        self, limit: int = 20, page: int = 1
    ) -> List[Dict[str, Any]]:
        """Gets paginated commit history."""
        if self.repo.head_is_unborn:
            return []

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

    def _get_commit_diff(self, commit: pygit2.Commit) -> pygit2.Diff:
        """Helper to get the diff of a commit against its parent."""
        if not commit.parents:
            empty_tree_oid = self.repo.TreeBuilder().write()
            empty_tree = self.repo.get(empty_tree_oid)
            return empty_tree.diff_to_tree(commit.tree)
        else:
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

    def list_branches(self) -> Dict[str, Any]:
        """Lists all local and remote branches."""
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

        unique_branches = {(b["name"], b["is_remote"]): b for b in branches}.values()
        branches = sorted(
            list(unique_branches), key=lambda x: (x["is_remote"], x["name"])
        )
        return {"branches": branches, "current_branch": active_branch_name}
