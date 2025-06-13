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
        """Gets the status of the repository, returning a structured dictionary."""
        all_files = {}

        def get_path(diff):
            return diff.b_path or diff.a_path

        try:
            # Staged changes (Index vs. HEAD)
            for diff in self.repo.index.diff("HEAD"):
                all_files[get_path(diff)] = {
                    "path": get_path(diff),
                    "index_status": diff.change_type,
                    "work_tree_status": " ",
                    "original_path": diff.rename_from if diff.renamed else None,
                }
        except git.exc.BadName as e:  # Handles new repo with no HEAD
            logger.warning(f"Could not diff against HEAD (likely a new repo): {e}")

        # Unstaged changes (Working Tree vs. Index)
        for diff in self.repo.index.diff(None):
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
        """Adds a single file to the staging area."""
        self.repo.index.add([filepath])

    def add_all(self) -> None:
        """Adds all changes (tracked and untracked) to the staging area."""
        self.repo.git.add(A=True)

    def unstage_file(self, filepath: str) -> None:
        """Removes a single file from the staging area."""
        self.repo.index.reset("HEAD", paths=[filepath])

    def unstage_all(self) -> None:
        """Removes all files from the staging area."""
        self.repo.index.reset("HEAD")

    def discard_file(self, filepath: str) -> None:
        """Discards changes to a single unstaged file."""
        if filepath in self.repo.untracked_files:
            full_path = os.path.join(self.repo_path, filepath)
            os.remove(full_path)
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
        autostash: bool = True,
    ) -> str:
        """Pulls changes from a remote. Returns the fetch summary."""
        remote = self._get_remote(remote_name)
        try:
            fetch_info_list = remote.pull(
                refspec=branch or self.default_branch,
                rebase=rebase,
                autostash=autostash,
            )
            messages = [info.note for info in fetch_info_list if info.note]
            return "\n".join(messages) or "Pull successful."
        except GitPythonError as e:
            if "Merge conflict" in e.stderr or "Automatic merge failed" in e.stderr:
                logger.warning("Conflict detected during pull. Aborting...")
                try:
                    self.repo.git.merge("--abort")
                except GitPythonError:
                    self.repo.git.rebase("--abort")
                raise MergeConflictError(
                    f"Conflict detected during pull. Please resolve manually. Details: {e.stderr}"
                ) from e
            raise

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
        """Corrected Workflow: Pulls (with rebase), adds, commits, and pushes."""
        logger.info("Starting workspace sync...")
        results = {}

        try:
            results["pull"] = self.pull_remote_changes(
                remote_name=remote_name, rebase=True, autostash=True
            )
            logger.info("Sync: Pull successful.")
        except RemoteNotFoundError:
            logger.info("Sync: No remote configured, skipping pull and push.")
            results["pull"] = "skipped_no_remote"
            results["push"] = "skipped_no_remote"

        self.add_all()
        results["add"] = "success"
        logger.info("Sync: All changes added.")

        try:
            results["commit"] = self.commit(commit_message)
            logger.info(f"Sync: Changes committed ({results['commit'][:7]}).")
        except NoChangesError:
            results["commit"] = "no_changes"
            logger.info("Sync: No changes to commit.")

        if results.get("push") != "skipped_no_remote":
            try:
                results["push"] = self.push_local_changes(remote_name=remote_name)
                logger.info("Sync: Push successful.")
            except GitPythonError as e:
                if "Everything up-to-date" in str(e):
                    results["push"] = "up_to_date"
                else:
                    raise

        logger.info("Workspace sync completed successfully.")
        return results

    # --- Query/Utility Methods ---
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
            else self.repo.tree(
                "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
            )  # Empty tree
        )
        diffs = parent.diff(commit, create_patch=False)

        changed_files = []
        for diff in diffs:
            changed_files.append(
                {"status": diff.change_type, "path": diff.b_path or diff.a_path}
            )
        return changed_files

    def list_branches(self) -> Dict[str, Any]:
        """Corrected logic to list all local and remote branches."""
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
                # e.g., 'origin/main' -> 'main'
                remote_branch_name = ref.name.split("/", 1)[-1]
                if remote_branch_name == "HEAD":
                    continue
                # Add if no local branch of the same name exists, to avoid duplicates in simple UIs
                if remote_branch_name not in local_branch_names:
                    all_branches.append(
                        {"name": ref.name, "is_active": False, "is_remote": True}
                    )

        return {"branches": all_branches, "current_branch": active_branch_name}

    def switch_branch(self, branch_name: str) -> None:
        """Switches to a different local or remote branch."""
        try:
            if "/" in branch_name:  # Assumes remote branch
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
            else:  # Local branch
                self.repo.heads[branch_name].checkout()
        except KeyError:
            raise BranchNotFoundError(f"Local branch '{branch_name}' not found.")

    def get_current_branch(self) -> Optional[str]:
        try:
            branch_name = self.repo.git.rev_parse("--abbrev-ref", "HEAD")
            return branch_name if branch_name != "HEAD" else "HEAD (Detached)"
        except GitPythonError as e:
            if "fatal: bad revision 'HEAD'" in e.stderr:
                return None
            raise

    def get_status_summary(self) -> Dict[str, Any]:
        staged_len = 0
        try:
            self.repo.head.commit
            staged_len = len(self.repo.index.diff("HEAD"))
        except ValueError:
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

    # --- Helper/Private Methods ---
    def _get_remote(self, remote_name: Optional[str] = None) -> git.Remote:
        """Safely gets a remote, raising a specific error if not found."""
        remote_to_use_name = remote_name or self.default_remote
        try:
            return self.repo.remotes[remote_to_use_name]
        except IndexError:
            raise RemoteNotFoundError(f"Remote '{remote_to_use_name}' not found.")

    def _format_commit_message(self, template: str) -> str:
        """Replaces placeholders in a commit message template."""
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        template = template.replace("{{date}}", current_date)
        if "{{numFiles}}" in template:
            staged_files_count = len(self.repo.index.diff("HEAD"))
            template = template.replace("{{numFiles}}", str(staged_files_count))
        return template
