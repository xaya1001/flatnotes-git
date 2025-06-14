# server/git_integration/git_manager.py
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import git
from git import Actor
from git import GitCommandError as GitPythonError

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
    """An object-oriented wrapper for GitPython operations."""

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
        self.author = Actor(user_name, user_email) if user_name and user_email else None
        self.repo: git.Repo

        try:
            self.repo = git.Repo(repo_path)
            ssh_cmd = os.environ.get("GIT_SSH_COMMAND")
            if ssh_cmd:
                self.repo.git.update_environment(GIT_SSH_COMMAND=ssh_cmd)
        except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError) as e:
            raise RepositoryInvalidError(
                f"Invalid or missing repository at '{repo_path}': {e}"
            ) from e

        logger.info(f"GitManager initialized for repository at: {self.repo_path}")

    # --- Core Methods ---
    def get_status(self) -> Dict[str, Any]:
        """Gets the status of the repository by directly reporting diff states."""
        all_files: Dict[str, Dict[str, Any]] = {}

        def get_path(diff):
            return diff.a_path or diff.b_path

        try:
            # Staged changes (Index vs. HEAD)
            # We now trust diff.change_type because the action methods are correct.
            for diff in self.repo.index.diff("HEAD", R=True):
                filepath = get_path(diff)
                all_files[filepath] = {
                    "path": filepath,
                    "index_status": diff.change_type,
                    "work_tree_status": " ",
                    "original_path": diff.rename_from if diff.renamed else None,
                }
        except git.exc.BadName:  # Handles new repo with no HEAD
            pass  # Unstaged changes will cover initial adds

        # Unstaged changes (Working Tree vs. Index)
        for diff in self.repo.index.diff(None, R=True):
            filepath = get_path(diff)
            if filepath in all_files:
                all_files[filepath]["work_tree_status"] = diff.change_type
            else:
                all_files[filepath] = {
                    "path": filepath,
                    "index_status": " ",
                    "work_tree_status": diff.change_type,
                    "original_path": diff.rename_from if diff.renamed else None,
                }
        # Untracked files
        for filepath in self.repo.untracked_files:
            all_files[filepath] = {
                "path": filepath,
                "index_status": "?",
                "work_tree_status": "?",
                "original_path": None,
            }

        return {
            "files": list(all_files.values()),
            "current_branch": self.get_current_branch(),
        }

    def add_file(self, filepath: str) -> None:
        """
        Stages a single file. Correctly handles additions, modifications,
        and deletions using the appropriate high-level gitpython commands.
        """
        if os.path.exists(os.path.join(self.repo_path, filepath)):
            # Use the standard 'add' for existing/modified files.
            self.repo.index.add([filepath])
        else:
            # Use the 'remove' command for deleted files.
            self.repo.index.remove([filepath], working_tree=False)

    def add_all(self) -> None:
        """Adds all changes (tracked and untracked) to the staging area."""
        self.repo.git.add(A=True)

    def unstage_file(self, filepath: str) -> None:
        """Removes a single file from the staging area."""
        # Use '--' to disambiguate paths from revisions.
        self.repo.git.reset("HEAD", "--", filepath)

    def unstage_all(self) -> None:
        """Removes all files from the staging area."""
        self.repo.index.reset("HEAD")

    def discard_file(self, filepath: str) -> None:
        """Discards changes to a single unstaged file."""
        if filepath in self.repo.untracked_files:
            self.repo.git.clean("-fd", "--", filepath)
        else:
            self.repo.git.checkout("--", filepath)

    def discard_all(self) -> None:
        """Discards all unstaged changes and removes untracked files."""
        self.repo.git.restore("--", ".")
        self.repo.git.clean("-fd")

    def commit(self, message: str) -> str:
        """Commits staged changes. Returns the commit hash."""
        if not message.strip():
            raise ValueError("Commit message cannot be empty.")
        if not self.repo.index.diff("HEAD"):
            # Check for initial commit case
            if self.repo.head.is_valid():
                raise NoChangesError("No changes staged for commit.")

        formatted_message = self._format_commit_message(message)
        commit_obj = self.repo.index.commit(
            formatted_message, author=self.author, committer=self.author
        )
        return commit_obj.hexsha

    def pull_remote_changes(
        self,
        remote_name: Optional[str] = None,
        branch: Optional[str] = None,
        rebase: bool = False,
    ) -> str:
        """
        Pulls changes from a remote. This operation is designed to be safe and
        will not leave the working directory in a conflicted state.
        """
        remote = self._get_remote(remote_name)
        current_branch = branch or self.default_branch

        stashed_changes = self.repo.git.stash()
        logger.debug(f"Stash result: {stashed_changes}")

        try:
            fetch_info_list = remote.pull(
                refspec=current_branch,
                rebase=rebase,
            )
            messages = [info.note for info in fetch_info_list if info.note]
            output = "\n".join(messages) or "Pull successful."

        except GitPythonError as e:
            logger.warning(f"Git pull failed. stderr: {e.stderr}")
            self.repo.git.reset("--hard", "ORIG_HEAD")
            raise MergeConflictError(
                f"Conflict detected during pull. The operation was safely aborted, "
                f"and your local files are unchanged. Please resolve conflicts manually using the command line. "
                f"Details: {e.stderr}"
            ) from e
        finally:
            if "No local changes to save" not in stashed_changes:
                try:
                    self.repo.git.stash("pop")
                    logger.debug("Stash popped successfully.")
                except GitPythonError as stash_err:
                    logger.error(f"Failed to pop stash after pull: {stash_err.stderr}")
                    raise GitManagerError(
                        "Pull succeeded, but could not restore your uncommitted changes from the stash. "
                        "Please run `git stash pop` manually."
                    ) from stash_err
        return output

    def push_local_changes(
        self,
        remote_name: Optional[str] = None,
        branch: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """Pushes local changes to a remote. Returns the push summary."""
        remote = self._get_remote(remote_name)
        push_info_list = remote.push(refspec=branch or self.default_branch, force=force)
        for info in push_info_list:
            if info.flags & (info.ERROR | info.REJECTED):
                raise GitPythonError(
                    f"push {remote.name}", info.flags, info.summary, info.summary
                )
        return "Push successful."

    def sync_workspace(
        self, commit_message: str, remote_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Safely synchronizes the workspace. It commits local changes, pulls remote
        changes (with rebase), and pushes. The pull operation is conflict-safe.
        """
        logger.info("Starting safe workspace sync...")
        results = {}

        self.add_all()
        try:
            commit_hash = self.commit(commit_message)
            results["commit"] = commit_hash
        except NoChangesError:
            results["commit"] = "no_changes_to_commit"

        try:
            results["pull"] = self.pull_remote_changes(
                remote_name=remote_name, rebase=True
            )
        except RemoteNotFoundError:
            results["pull"] = "skipped_no_remote"
            results["push"] = "skipped_no_remote"
            return results

        if results.get("push") != "skipped_no_remote":
            results["push"] = self.push_local_changes(remote_name=remote_name)

        logger.info("Workspace sync completed successfully.")
        return results

    def get_commit_log(self, limit: int = 10, page: int = 1) -> List[Dict[str, Any]]:
        skip_count = (page - 1) * limit
        try:
            commits = list(self.repo.iter_commits(max_count=limit, skip=skip_count))
        except git.exc.GitCommandError as e:
            if "does not have any commits yet" in e.stderr.lower():
                return []
            raise
        return [
            {
                "hash": c.hexsha,
                "author_name": c.author.name,
                "author_email": c.author.email,
                "date": c.authored_datetime.isoformat(),
                "message": c.message.strip(),
            }
            for c in commits
        ]

    def get_files_in_commit(self, commit_hash: str) -> List[Dict[str, str]]:
        commit = self.repo.commit(commit_hash)
        parent = (
            commit.parents[0]
            if commit.parents
            else self.repo.tree("4b825dc642cb6eb9a060e54bf8d69288fbee4904")
        )
        diffs = parent.diff(commit, create_patch=False)
        return [
            {"status": diff.change_type, "path": diff.b_path or diff.a_path}
            for diff in diffs
        ]

    def list_branches(self) -> Dict[str, Any]:
        active_branch_name = self.get_current_branch()
        all_branches = []
        local_branch_names = {b.name for b in self.repo.branches}

        for b in self.repo.branches:
            all_branches.append(
                {
                    "name": b.name,
                    "is_active": b.name == active_branch_name,
                    "is_remote": False,
                }
            )

        for r in self.repo.remotes:
            for ref in r.refs:
                remote_branch_name = ref.name.split("/", 1)[-1]
                if remote_branch_name == "HEAD":
                    continue
                if remote_branch_name not in local_branch_names:
                    all_branches.append(
                        {"name": ref.name, "is_active": False, "is_remote": True}
                    )
        return {"branches": all_branches, "current_branch": active_branch_name}

    def switch_branch(self, branch_name: str) -> None:
        try:
            if "/" in branch_name:
                remote_name, remote_branch_name = branch_name.split("/", 1)
                remote = self._get_remote(remote_name)
                remote_ref = next(
                    (ref for ref in remote.refs if ref.name == branch_name), None
                )
                if not remote_ref:
                    raise BranchNotFoundError(
                        f"Remote branch '{branch_name}' not found."
                    )
                new_local_branch = self.repo.create_head(remote_branch_name, remote_ref)
                new_local_branch.set_tracking_branch(remote_ref)
                new_local_branch.checkout()
            else:
                self.repo.heads[branch_name].checkout()
        except KeyError:
            raise BranchNotFoundError(f"Local branch '{branch_name}' not found.")

    def get_current_branch(self) -> Optional[str]:
        try:
            return self.repo.active_branch.name
        except TypeError:  # Detached HEAD
            return "HEAD (Detached)"
        except git.exc.BadName:
            return None

    def get_status_summary(self) -> Dict[str, Any]:
        try:
            staged_len = len(self.repo.index.diff("HEAD"))
        except git.exc.BadName:
            staged_len = len(self.repo.index.diff(None))

        changed_files_count = (
            staged_len
            + len(self.repo.index.diff(None))
            + len(self.repo.untracked_files)
        )
        return {
            "current_branch": self.get_current_branch(),
            "files_changed_count": changed_files_count,
        }

    def get_remote_url(self, remote_name: Optional[str] = None) -> Optional[str]:
        try:
            remote = self._get_remote(remote_name)
            return next(remote.urls, None)
        except RemoteNotFoundError:
            return None

    def _get_remote(self, remote_name: Optional[str] = None) -> git.Remote:
        remote_to_use_name = remote_name or self.default_remote
        try:
            return self.repo.remotes[remote_to_use_name]
        except IndexError:
            raise RemoteNotFoundError(f"Remote '{remote_to_use_name}' not found.")

    def _format_commit_message(self, template: str) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        template = template.replace("{{date}}", current_date)
        if "{{numFiles}}" in template:
            try:
                staged_files_count = len(self.repo.index.diff("HEAD"))
            except git.exc.BadName:
                staged_files_count = len(self.repo.index.diff(None))
            template = template.replace("{{numFiles}}", str(staged_files_count))
        return template
