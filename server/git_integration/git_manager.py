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
        """
        Gets the status of the repository using a hybrid approach to ensure
        reliability, especially for deleted files.
        """
        all_files: Dict[str, Dict[str, Any]] = {}

        def get_path(diff):
            return diff.a_path or diff.b_path

        # --- Stage 1: Staged Changes (Index vs. HEAD) ---
        try:
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

        # --- Stage 2: Unstaged Modifications & Deletions ---

        # Part A: Detect unstaged MODIFICATIONS using diff. This is reliable for existing files.
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

        # Part B : Manually detect unstaged DELETIONS.
        # This is more reliable than relying on the diff for deleted file detection.
        indexed_files = {path for path, _ in self.repo.index.entries}
        for filepath in indexed_files:
            # If a file is in the index but not on disk, it's a working-tree deletion.
            if not os.path.exists(os.path.join(self.repo.working_dir, filepath)):
                # Only mark as deleted if it's not already staged as deleted.
                if (
                    filepath not in all_files
                    or all_files[filepath]["index_status"] != "D"
                ):
                    if filepath in all_files:
                        all_files[filepath]["work_tree_status"] = "D"
                    else:
                        all_files[filepath] = {
                            "path": filepath,
                            "index_status": " ",
                            "work_tree_status": "D",
                            "original_path": None,
                        }

        # --- Stage 3: Untracked Files ---
        for filepath in self.repo.untracked_files:
            if filepath not in all_files:
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
        will not leave the working directory in a conflicted state. It uses a
        safe stash-apply-drop sequence to protect local changes.
        """
        remote = self._get_remote(remote_name)
        current_branch = branch or self.default_branch

        # Stash local changes if there are any
        stashed_changes = self.repo.git.stash()
        logger.debug(f"Stash result: {stashed_changes}")

        try:
            # Pull remote changes
            fetch_info_list = remote.pull(
                refspec=current_branch,
                rebase=rebase,
            )
            messages = [info.note for info in fetch_info_list if info.note]
            output = "\n".join(messages) or "Pull successful."

        except GitPythonError as e:
            # This handles conflicts during the PULL itself.
            logger.warning(f"Git pull failed. stderr: {e.stderr}")
            # The pull failed, so we can safely pop the original stash back.
            if "No local changes to save" not in stashed_changes:
                self.repo.git.stash("pop")
            raise MergeConflictError(
                "Conflict detected during pull. The operation was safely aborted, "
                "and your local files are unchanged. "
                "Please resolve conflicts manually using the command line."
            ) from e

        # If we had local changes, we now try to re-apply them safely.
        if "No local changes to save" not in stashed_changes:
            try:
                # 1. Apply the stash but DO NOT drop it from the stack yet.
                self.repo.git.stash("apply")
                logger.debug("Stash applied successfully.")

                # 2. Check if the apply resulted in conflicts.
                # `git status --porcelain` shows 'UU' for unmerged (conflicted) files.
                status_output = self.repo.git.status("--porcelain")
                if "UU " in status_output:
                    # 3. CONFLICT DETECTED.
                    # Reset the working directory to a clean state, removing conflict markers.
                    self.repo.git.reset("--hard")
                    logger.error(
                        "Conflict detected while applying stashed changes after a pull. Stash is preserved."
                    )
                    # The stash is still on the stack because we used `apply`.
                    # Raise a clear error to the user.
                    raise MergeConflictError(
                        "Pull was successful, but your local changes could not be automatically reapplied due to a conflict. "
                        "Your uncommitted work has been safely preserved in a stash. "
                        "Please resolve this manually via the command line (e.g., using 'git stash pop')."
                    )

                # 4. NO CONFLICT. The apply was clean. Now we can safely drop the stash.
                self.repo.git.stash("drop")
                logger.debug("Stash dropped successfully after clean apply.")

            except GitPythonError as stash_err:
                # This catches other errors during the apply/drop process.
                logger.error(f"Failed to re-apply stash after pull: {stash_err.stderr}")
                # The stash is preserved because we haven't dropped it yet.
                raise GitManagerError(
                    "Pull succeeded, but could not restore your uncommitted changes from the stash. "
                    "Please run `git stash apply` manually to investigate."
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

    def fetch_and_list_branches(self) -> Dict[str, Any]:
        """
        Fetches all remotes to update local refs and then lists all branches.
        This ensures remote branches are visible.
        """
        try:
            # Fetch from all remotes to get the latest branches
            for remote in self.repo.remotes:
                logger.info(f"Fetching from remote '{remote.name}'...")
                remote.fetch(prune=True)
            logger.info("Fetch complete.")
        except GitPythonError as e:
            logger.error(f"Failed to fetch remotes: {e.stderr}")
            # We can choose to fail here or just proceed with the old data.
            # It's better to show potentially stale data than crash.
            # We will still log the error for diagnostics.
            # Let's add a log entry for the user to see.
            from .log_handler import LogLevel, add_git_log

            add_git_log(LogLevel.WARN, "Could not refresh remote branches.", str(e))

        # Now, call the existing list_branches method on the updated repo state
        return self.list_branches()

    def list_branches(self) -> Dict[str, Any]:
        active_branch_name = self.get_current_branch()
        all_branches = []
        # Use a set to track branch names to avoid duplicates from remote/local
        seen_branches = set()

        # Add local branches first
        for b in self.repo.branches:
            if b.name not in seen_branches:
                all_branches.append(
                    {
                        "name": b.name,
                        "is_active": b.name == active_branch_name,
                        "is_remote": False,
                    }
                )
                seen_branches.add(b.name)

        # Add remote branches that don't have a local counterpart
        for r in self.repo.remotes:
            for ref in r.refs:
                # remote_branch_name is like 'origin/main', we want just 'main' for comparison
                # and the full 'origin/main' for display/checkout
                branch_name_part = ref.name.split("/", 1)[-1]
                if branch_name_part == "HEAD":
                    continue
                if branch_name_part not in seen_branches:
                    all_branches.append(
                        {
                            "name": ref.name,  # Use full name like 'origin/new-feature'
                            "is_active": False,
                            "is_remote": True,
                        }
                    )
                    seen_branches.add(branch_name_part)

        # Sort branches for easier reading, current branch can be handled on frontend
        all_branches.sort(key=lambda x: (x["is_remote"], x["name"]))

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
