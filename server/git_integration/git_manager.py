# server/git_integration/git_manager.py
import os  # <--- 1. 添加 os 模块的导入
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pygit2
from pygit2 import GitError, Signature
from pygit2.enums import FileStatus

from logger import logger


# --- Custom Exceptions for Clearer Error Handling ---
class GitManagerError(Exception):
    """Base exception for the GitManager."""


class RepositoryInvalidError(GitManagerError):
    """Raised when the repository is not valid or accessible."""


class MergeConflictError(GitManagerError):
    """Raised when a pull operation results in a merge conflict."""


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
                raise RepositoryInvalidError(
                    f"No Git repository found at or above '{repo_path}'"
                )
            self.repo = pygit2.Repository(git_repo_path)
        except GitError as e:
            raise RepositoryInvalidError(
                f"Invalid repository at '{repo_path}': {e}"
            ) from e

        logger.info(f"GitManager initialized for repository at: {self.repo.path}")

    def _run_git_command(self, command: List[str]) -> str:
        try:
            process = subprocess.run(
                ["git"] + command,
                cwd=self.repo.workdir,
                capture_output=True,
                text=True,
                check=True,
            )
            return process.stdout
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Git command `{' '.join(command)}` failed. stderr: {e.stderr}"
            )
            if "conflict" in e.stderr.lower():
                raise MergeConflictError(e.stderr)
            raise GitManagerError(e.stderr)

    def _format_remote_url_for_web(self, url: str) -> Optional[str]:
        """
        Converts SSH or HTTPS git URLs to a browsable web URL.
        This version is simplified and robust, based on debug logs.
        """
        if not url:
            return None

        # Handle SSH: git@github.com:user/repo.git -> https://github.com/user/repo
        if url.startswith("git@"):
            path = url.split("@", 1)[1].replace(":", "/", 1)
            base_url = f"https://{path}"
            return base_url.removesuffix(".git").removesuffix("/")

        # Handle HTTP(S): https://github.com/user/repo.git -> https://github.com/user/repo
        if url.startswith(("http://", "https://")):
            return url.removesuffix(".git").removesuffix("/")

        logger.warning(f"Could not parse remote URL format: {url}")
        return None

    def _map_status_flags(self, status_flags: FileStatus) -> Dict[str, str]:
        index_char = " "
        work_tree_char = " "
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
            index_char = "U"
            work_tree_char = "U"
        if work_tree_char == "?":
            index_char = "?"
        return {"index": index_char, "work_tree": work_tree_char}

    def get_ahead_behind(self) -> Tuple[int, int]:
        if self.repo.head_is_unborn or self.repo.head_is_detached:
            return 0, 0
        current_branch_name = self.repo.head.shorthand
        local_branch = self.repo.branches.get(current_branch_name)
        if not local_branch:
            return 0, 0
        upstream = local_branch.upstream
        if not upstream:
            return 0, 0
        local_commit_oid = local_branch.target
        upstream_commit_oid = upstream.target
        if not local_commit_oid or not upstream_commit_oid:
            return 0, 0
        try:
            ahead, behind = self.repo.ahead_behind(
                local_commit_oid, upstream_commit_oid
            )
            return ahead, behind
        except GitError as e:
            logger.warning(
                f"Could not calculate ahead/behind for branch '{current_branch_name}': {e}"
            )
            return 0, 0

    def get_status(self) -> Dict[str, Any]:
        status_result = self.repo.status()
        all_files = []
        for filepath, flags in status_result.items():
            if flags == FileStatus.CURRENT or flags == FileStatus.IGNORED:
                continue
            status_chars = self._map_status_flags(flags)
            all_files.append(
                {
                    "path": filepath,
                    "index_status": status_chars["index"],
                    "work_tree_status": status_chars["work_tree"],
                    "original_path": None,
                }
            )
        ahead, behind = self.get_ahead_behind()
        return {
            "files": all_files,
            "current_branch": self.get_current_branch(),
            "commits_ahead": ahead,
            "commits_behind": behind,
        }

    def add_file(self, filepath: str) -> None:
        status = self.repo.status()
        file_status_flags = status.get(filepath)
        if file_status_flags is None:
            logger.warning(
                f"Attempted to stage '{filepath}', but it's not tracked or has no changes."
            )
            return
        if file_status_flags & FileStatus.WT_DELETED:
            self.repo.index.remove(filepath)
        else:
            self.repo.index.add(filepath)
        self.repo.index.write()

    def add_all(self) -> None:
        self.repo.index.add_all()
        self.repo.index.write()

    def unstage_file(self, filepath: str) -> None:
        if self.repo.head_is_unborn:
            try:
                self.repo.index.remove(filepath)
                self.repo.index.write()
            except KeyError:
                pass
            return
        head_commit = self.repo.head.peel()
        try:
            tree_entry = head_commit.tree[filepath]
            new_index_entry = pygit2.IndexEntry(
                filepath, tree_entry.id, tree_entry.filemode
            )
            self.repo.index.add(new_index_entry)
        except KeyError:
            self.repo.index.remove(filepath)
        self.repo.index.write()

    def unstage_all(self) -> None:
        if self.repo.head_is_unborn:
            self.repo.index.clear()
        else:
            self.repo.index.read_tree(self.repo.head.peel(pygit2.Tree))
        self.repo.index.write()

    def discard_file(self, filepath: str) -> None:
        """Discards changes to a single file. Deletes if untracked, otherwise checkouts."""
        status = self.repo.status()
        file_status_flags = status.get(filepath)

        # If the file is untracked (e.g., a new file not yet added to git)
        if file_status_flags and file_status_flags & FileStatus.WT_NEW:
            full_path = os.path.join(self.repo.workdir, filepath)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Removed untracked file: {filepath}")
            else:
                logger.warning(
                    f"Attempted to discard untracked file, but it does not exist: {filepath}"
                )
        # For all other changes (modified, deleted tracked files etc.)
        else:
            self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE, paths=[filepath])
            logger.info(f"Reverted changes to tracked file: {filepath}")

    def discard_all(self) -> None:
        """Discards all changes in the working directory, including untracked files."""
        # First, revert all changes to tracked files
        self.repo.checkout(strategy=pygit2.GIT_CHECKOUT_FORCE)
        logger.info("Reverted all changes to tracked files.")

        # Then, remove all untracked files and directories
        # pygit2 does not have a 'clean' method, so we use subprocess
        try:
            self._run_git_command(["clean", "-fd"])
            logger.info("Cleaned all untracked files and directories.")
        except GitManagerError as e:
            logger.error(f"Failed to clean untracked files: {e}")
            # We raise the exception to let the caller know the operation may be incomplete
            raise

    def commit(self, message: str) -> str:
        if not message.strip():
            raise ValueError("Commit message cannot be empty.")
        status = self.repo.status()
        if not status:
            raise NoChangesError("No changes in the repository to commit.")
        if self.repo.head_is_unborn:
            if not self.repo.index:
                raise NoChangesError("No changes staged for commit.")
        elif self.repo.index.diff_to_tree(self.repo.head.peel().tree).patch is None:
            raise NoChangesError("No changes staged for commit.")
        formatted_message = self._format_commit_message(message)
        parents = [] if self.repo.head_is_unborn else [self.repo.head.target]
        tree = self.repo.index.write_tree()
        commit_oid = self.repo.create_commit(
            "HEAD", self.author, self.committer, formatted_message, tree, parents
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
        current_branch = branch or self.get_current_branch() or self.default_branch
        old_head_hash = (
            str(self.repo.head.target) if not self.repo.head_is_unborn else None
        )
        command = ["pull", remote, current_branch]
        if rebase:
            command.append("--rebase")
        output = self._run_git_command(command)
        changed_files = []
        if not self.repo.head_is_unborn and old_head_hash != str(self.repo.head.target):
            new_head_hash = str(self.repo.head.target)
            diff = self.repo.diff(old_head_hash, new_head_hash)
            changed_files = [
                {"path": d.delta.new_file.path, "change_type": d.delta.status_char()}
                for d in diff
            ]
        return {"message": output, "changed_files": changed_files}

    def push_local_changes(
        self,
        remote_name: Optional[str] = None,
        branch: Optional[str] = None,
        force: bool = False,
    ) -> str:
        remote = remote_name or self.default_remote
        current_branch = branch or self.get_current_branch() or self.default_branch
        command = ["push", remote, current_branch]
        if force:
            command.append("--force")
        return self._run_git_command(command)

    def sync_workspace(
        self, commit_message: str, remote_name: Optional[str] = None
    ) -> Dict[str, Any]:
        results = {}
        has_pending_changes = bool(self.repo.status())
        if has_pending_changes:
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
                    "message": "No valid changes to commit.",
                }
        else:
            results["commit"] = {
                "hash": "no_changes",
                "message": "No local changes detected.",
            }
        try:
            pull_result = self.pull_remote_changes(remote_name=remote_name, rebase=True)
            results["pull"] = pull_result
            push_output = self.push_local_changes(remote_name=remote_name)
            results["push"] = {"message": push_output}
        except RemoteNotFoundError:
            results["pull"] = {"message": "skipped_no_remote"}
            results["push"] = {"message": "skipped_no_remote"}
        except GitManagerError as e:
            results["pull"] = {"message": f"failed: {e}", "changed_files": []}
            results["push"] = {"message": "skipped_due_to_pull_failure"}
            raise e
        return results

    def get_commit_log(self, limit: int = 20, page: int = 1) -> List[Dict[str, Any]]:
        if self.repo.head_is_unborn:
            return []
        try:
            self._run_git_command(["fetch", self.default_remote])
        except GitManagerError as e:
            logger.warning(f"Could not fetch from remote for log: {e}")
        upstream_commit_oid = None
        current_branch = self.repo.branches.get(self.get_current_branch())
        if current_branch and current_branch.upstream:
            upstream_branch = current_branch.upstream
            if upstream_branch.target:
                upstream_commit_oid = upstream_branch.target
        walker = self.repo.walk(self.repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL)
        all_commits = list(walker)
        paginated_commits = all_commits[(page - 1) * limit : page * limit]
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
        remote_to_use = remote_name or self.default_remote
        try:
            remote = self.repo.remotes[remote_to_use]
            return remote.url
        except (KeyError, GitError):
            logger.warning(f"Could not find remote URL for '{remote_to_use}'.")
            return None

    def get_current_branch(self) -> Optional[str]:
        if self.repo.head_is_unborn:
            return self.default_branch
        if self.repo.head_is_detached:
            return "HEAD (Detached)"
        return self.repo.head.shorthand

    def get_status_summary(self) -> Dict[str, Any]:
        status = self.repo.status()
        staged_count = 0
        unstaged_count = 0
        for _, flags in status.items():
            if flags == FileStatus.CURRENT or flags == FileStatus.IGNORED:
                continue
            if flags & (
                FileStatus.INDEX_NEW
                | FileStatus.INDEX_MODIFIED
                | FileStatus.INDEX_DELETED
                | FileStatus.INDEX_RENAMED
            ):
                staged_count += 1
            if flags & (
                FileStatus.WT_NEW
                | FileStatus.WT_MODIFIED
                | FileStatus.WT_DELETED
                | FileStatus.WT_RENAMED
            ):
                unstaged_count += 1
        ahead, behind = self.get_ahead_behind()
        return {
            "current_branch": self.get_current_branch(),
            "files_changed_count": staged_count + unstaged_count,
            "commits_ahead": ahead,
            "commits_behind": behind,
        }

    def _format_commit_message(self, template: str) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        template = template.replace("{{date}}", current_date)
        if "{{numFiles}}" in template:
            try:
                diff = self.repo.index.diff_to_tree(
                    self.repo.head.peel().tree if not self.repo.head_is_unborn else None
                )
                staged_files_count = diff.stats.files_changed
            except (KeyError, GitError):
                staged_files_count = len(self.repo.index)
            template = template.replace("{{numFiles}}", str(staged_files_count))
        return template

    def fetch_and_list_branches(self) -> Dict[str, Any]:
        try:
            self._run_git_command(["fetch", self.default_remote, "--prune"])
        except GitManagerError as e:
            logger.warning(f"Could not fetch from remote '{self.default_remote}': {e}")
        return self.list_branches()

    def list_branches(self) -> Dict[str, Any]:
        active_branch_name = self.get_current_branch()
        all_branches = []
        local_branch_names = set(self.repo.branches.local)
        for b_name in local_branch_names:
            all_branches.append(
                {
                    "name": b_name,
                    "is_active": b_name == active_branch_name,
                    "is_remote": False,
                }
            )
        for b_name in self.repo.branches.remote:
            remote_name, branch_name_part = b_name.split("/", 1)
            if branch_name_part not in local_branch_names:
                all_branches.append(
                    {"name": branch_name_part, "is_active": False, "is_remote": True}
                )
        all_branches.sort(key=lambda x: (x["is_remote"], x["name"]))
        return {"branches": all_branches, "current_branch": active_branch_name}

    def switch_branch(self, branch_name: str) -> None:
        if branch_name in self.repo.branches.local:
            branch = self.repo.branches.local[branch_name]
            self.repo.checkout(branch)
        else:
            remote_branch_name = f"{self.default_remote}/{branch_name}"
            if remote_branch_name in self.repo.branches.remote:
                remote_branch = self.repo.branches.remote[remote_branch_name]
                new_branch = self.repo.create_branch(branch_name, remote_branch.peel())
                self.repo.checkout(new_branch)
                new_branch.upstream = remote_branch
            else:
                raise BranchNotFoundError(
                    f"Branch '{branch_name}' not found locally or in remote '{self.default_remote}'."
                )

    def checkout_file_from_commit(self, commit_hash: str, filepath: str) -> None:
        try:
            commit = self.repo.get(commit_hash)
            if not isinstance(commit, pygit2.Commit):
                raise GitError(f"Hash '{commit_hash}' does not point to a commit.")
            self.repo.checkout_tree(
                treeish=commit.tree,
                paths=[filepath],
                strategy=pygit2.GIT_CHECKOUT_FORCE,
            )
        except KeyError:
            raise FileNotFoundError(
                f"File '{filepath}' not found in commit '{commit_hash[:7]}'."
            )
        except Exception as e:
            logger.error(
                f"Failed to checkout file '{filepath}' from commit '{commit_hash}': {e}"
            )
            raise

    def reset_to_remote(
        self, remote_name: Optional[str] = None, branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        remote_to_use = remote_name or self.default_remote
        branch_to_use = branch_name or self.get_current_branch()
        if not branch_to_use:
            raise BranchNotFoundError(
                "Could not determine the current branch to reset."
            )
        try:
            self._run_git_command(["fetch", remote_to_use])
        except GitManagerError as e:
            logger.error(f"Failed to fetch before reset: {e}")
            raise GitManagerError(
                f"Could not fetch from remote '{remote_to_use}' before resetting. Aborting."
            )
        local_branch = self.repo.branches.get(branch_to_use)
        if not local_branch or not local_branch.upstream:
            raise GitManagerError(
                f"Branch '{branch_to_use}' does not have a configured upstream branch. Cannot reset."
            )
        upstream_commit_oid = local_branch.upstream.target
        if not upstream_commit_oid:
            raise GitManagerError(
                f"Upstream for branch '{branch_to_use}' is not valid."
            )
        self.repo.reset(upstream_commit_oid, pygit2.GIT_RESET_HARD)
        return {
            "message": f"Successfully reset branch '{branch_to_use}' to remote state.",
            "reset_to_hash": str(upstream_commit_oid),
        }
