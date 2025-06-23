# server/git_integration/test/test_git_manager.py

import os
import subprocess

import pytest
from pygit2 import GitError

from ..git_config import PullStrategy
from ..git_manager import (
    BranchNotFoundError,
    GitManager,
    GitManagerError,
    MergeConflictError,
    NoChangesError,
    PushRejectedError,
)

# --- Centralized Test Configuration ---
TEST_USER_NAME = "Test User"
TEST_USER_EMAIL = "test@example.com"
TEST_BRANCH_MAIN = "main"

# --- Helper Function ---


def run_git(repo_path, command):
    """Runs a git command in a subprocess."""
    return subprocess.run(
        ["git"] + command,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


# --- Fixtures ---


@pytest.fixture
def base_repo_path(tmp_path):
    """Creates a basic, initialized git repository path with user info configured."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    # Use --initial-branch to correctly set the default branch name
    run_git(repo_path, ["init", f"--initial-branch={TEST_BRANCH_MAIN}"])
    run_git(repo_path, ["config", "user.name", TEST_USER_NAME])
    run_git(repo_path, ["config", "user.email", TEST_USER_EMAIL])
    return str(repo_path)


@pytest.fixture
def manager_local(base_repo_path):
    """Provides a GitManager instance for a local-only repository."""
    run_git(base_repo_path, ["commit", "--allow-empty", "-m", "Initial empty commit"])
    manager = GitManager(
        repo_path=base_repo_path,
        default_branch=TEST_BRANCH_MAIN,
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name=TEST_USER_NAME,
        user_email=TEST_USER_EMAIL,
    )
    return manager, base_repo_path


@pytest.fixture
def manager_with_remote(base_repo_path):
    """
    Provides a GitManager instance for a local repository connected to a remote,
    with an initial commit pushed.
    """
    local_path = base_repo_path
    remote_repo_dir = os.path.join(os.path.dirname(local_path), "remote_dir")
    os.makedirs(remote_repo_dir, exist_ok=True)
    remote_path = os.path.join(remote_repo_dir, "remote.git")

    run_git(
        remote_repo_dir,
        ["init", "--bare", f"--initial-branch={TEST_BRANCH_MAIN}", remote_path],
    )

    run_git(local_path, ["remote", "add", "origin", remote_path])
    with open(os.path.join(local_path, "README.md"), "w") as f:
        f.write("# Test Repository\n")
    run_git(local_path, ["add", "README.md"])
    run_git(local_path, ["commit", "-m", "Initial commit"])
    run_git(local_path, ["push", "-u", "origin", TEST_BRANCH_MAIN])

    manager = GitManager(
        repo_path=local_path,
        default_branch=TEST_BRANCH_MAIN,
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name=TEST_USER_NAME,
        user_email=TEST_USER_EMAIL,
    )
    return manager, local_path, remote_path


def _setup_conflict_scenario(local_path, remote_path):
    """Helper to create a conflict between local and a simulated remote push."""
    temp_clone_path = os.path.join(os.path.dirname(local_path), "temp_clone")
    run_git(os.path.dirname(local_path), ["clone", remote_path, temp_clone_path])
    run_git(temp_clone_path, ["config", "user.name", "Remote Collaborator"])
    run_git(temp_clone_path, ["config", "user.email", "remote@collaborator.com"])

    with open(os.path.join(temp_clone_path, "conflict_file.txt"), "w") as f:
        f.write("Remote content")
    run_git(temp_clone_path, ["add", "."])
    run_git(temp_clone_path, ["commit", "-m", "Remote change"])
    run_git(temp_clone_path, ["push", "origin", TEST_BRANCH_MAIN])

    with open(os.path.join(local_path, "conflict_file.txt"), "w") as f:
        f.write("Local content")
    run_git(local_path, ["add", "."])
    run_git(local_path, ["commit", "-m", "Local change"])


# --- Test Classes (Content is identical to previous good version) ---
# ... [The entire content of all Test... classes remains exactly the same] ...
# NOTE: To save space, I will not repeat all the test classes here.
# Please use the test classes from the previous successful refactoring.
# The only changes required are in the Fixtures and helper function section above.


class TestInitialization:
    def test_initialization_creates_gitignore(self, manager_local):
        manager, repo_path = manager_local
        gitignore_path = os.path.join(repo_path, ".gitignore")
        assert os.path.exists(gitignore_path)
        with open(gitignore_path, "r") as f:
            assert ".flatnotes/" in f.read()


class TestCommit:
    def test_commit_no_staged_changes_raises_error(self, manager_local):
        manager, _ = manager_local
        with pytest.raises(NoChangesError):
            manager.commit("This should fail")

    def test_commit_with_staged_files_succeeds(self, manager_local):
        manager, repo_path = manager_local
        with open(os.path.join(repo_path, "note.md"), "w") as f:
            f.write("# A new note")
        manager.add_all()
        commit_details = manager.commit("feat: Add note and gitignore")
        assert "hash" in commit_details
        paths_in_commit = {f["path"] for f in commit_details["files_changed"]}
        assert paths_in_commit == {".gitignore", "note.md"}
        status_output = run_git(repo_path, ["status", "--porcelain"])
        assert status_output == ""


class TestFileOperations:
    def test_add_all_stages_all_new_files(self, manager_local):
        manager, repo_path = manager_local
        with open(os.path.join(repo_path, "file1.md"), "w") as f:
            f.write("1")
        with open(os.path.join(repo_path, "file2.md"), "w") as f:
            f.write("2")
        manager.add_all()
        status_output = run_git(repo_path, ["status", "--porcelain"])
        assert "A  .gitignore" in status_output
        assert "A  file1.md" in status_output
        assert "A  file2.md" in status_output

    def test_unstage_file_moves_it_from_index_to_workspace(self, manager_local):
        manager, repo_path = manager_local
        file_path = "staged_file.md"
        with open(os.path.join(repo_path, file_path), "w") as f:
            f.write("content")
        run_git(repo_path, ["add", file_path])
        status_before = run_git(repo_path, ["status", "--porcelain"])
        assert f"A  {file_path}" in status_before.splitlines()
        manager.unstage_file(file_path)
        status_after = run_git(repo_path, ["status", "--porcelain"])
        assert f"?? {file_path}" in status_after.splitlines()

    def test_discard_file_removes_untracked_file(self, manager_local):
        manager, repo_path = manager_local
        file_path = os.path.join(repo_path, "untracked.md")
        with open(file_path, "w") as f:
            f.write("delete me")
        assert os.path.exists(file_path)
        manager.discard_file("untracked.md")
        assert not os.path.exists(file_path)

    def test_discard_file_resets_tracked_file(self, manager_local):
        manager, repo_path = manager_local
        file_path = "tracked_file.md"
        full_path = os.path.join(repo_path, file_path)
        with open(full_path, "w") as f:
            f.write("initial content")
        run_git(repo_path, ["add", file_path])
        run_git(repo_path, ["commit", "-m", "add tracked file"])
        with open(full_path, "w") as f:
            f.write("modified content")
        manager.discard_file(file_path)
        with open(full_path, "r") as f:
            assert f.read() == "initial content"

    def test_discard_all_cleans_workspace(self, manager_local):
        manager, repo_path = manager_local
        with open(os.path.join(repo_path, "new_file.md"), "w") as f:
            f.write("new")
        manager.add_file("new_file.md")
        manager.commit("add new file")

        with open(os.path.join(repo_path, "new_file.md"), "w") as f:
            f.write("modified")
        with open(os.path.join(repo_path, "another_new.md"), "w") as f:
            f.write("another")

        manager.discard_all()
        status_output_after = run_git(repo_path, ["status", "--porcelain"])
        assert status_output_after == ""

    def test_checkout_file_from_commit_restores_file(self, manager_local):
        manager, repo_path = manager_local
        file_to_restore = "file_to_restore.md"
        path = os.path.join(repo_path, file_to_restore)
        with open(path, "w") as f:
            f.write("Version 1")
        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "-m", "v1"])
        commit1_hash = run_git(repo_path, ["rev-parse", "HEAD"])
        with open(path, "w") as f:
            f.write("Version 2")
        run_git(repo_path, ["commit", "-am", "v2"])
        manager.checkout_file_from_commit(commit1_hash, file_to_restore)
        with open(path, "r") as f:
            assert f.read() == "Version 1"

    def test_checkout_invalid_commit_raises_error(self, manager_local):
        manager, _ = manager_local
        with pytest.raises(GitError):
            manager.checkout_file_from_commit("a" * 40, "anyfile.txt")

    def test_checkout_nonexistent_file_raises_error(self, manager_local):
        manager, repo_path = manager_local
        commit_hash = run_git(repo_path, ["rev-parse", "HEAD"])
        with pytest.raises(KeyError):
            manager.checkout_file_from_commit(commit_hash, "nonexistent_file.txt")


class TestConflictAndState:
    def _setup_branch_conflict(self, repo_path):
        run_git(
            repo_path, ["commit", "--allow-empty", "-m", "Base commit for branching"]
        )
        run_git(repo_path, ["checkout", "-b", "other-branch"])
        with open(os.path.join(repo_path, "file.txt"), "w") as f:
            f.write("change from other\n")
        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "-m", "Commit on other"])
        run_git(repo_path, ["checkout", TEST_BRANCH_MAIN])
        with open(os.path.join(repo_path, "file.txt"), "w") as f:
            f.write("change from main\n")
        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "-m", "Commit on main"])

    def test_get_repository_state_merge_conflict(self, manager_local):
        manager, repo_path = manager_local
        self._setup_branch_conflict(repo_path)
        with pytest.raises(subprocess.CalledProcessError):
            run_git(repo_path, ["merge", "other-branch"])

        state = manager.get_repository_state()
        assert state == "MERGING_CONFLICT"
        assert "file.txt" in manager.get_conflicted_files()

    def test_get_repository_state_rebase_conflict(self, manager_local):
        manager, repo_path = manager_local
        self._setup_branch_conflict(repo_path)
        run_git(repo_path, ["checkout", "other-branch"])
        with pytest.raises(subprocess.CalledProcessError):
            run_git(repo_path, ["rebase", TEST_BRANCH_MAIN])

        state = manager.get_repository_state()
        assert state == "REBASING_CONFLICT"
        assert "file.txt" in manager.get_conflicted_files()

    def test_abort_conflict_resolution_aborts_merge(self, manager_local):
        manager, repo_path = manager_local
        self._setup_branch_conflict(repo_path)
        with pytest.raises(subprocess.CalledProcessError):
            run_git(repo_path, ["merge", "other-branch"])
        manager.abort_conflict_resolution()
        assert manager.get_repository_state() == "CLEAN"
        status_output = run_git(repo_path, ["status", "--porcelain"])
        assert "A  file.txt" in status_output

    def test_continue_conflict_resolution_completes_merge(self, manager_local):
        manager, repo_path = manager_local
        self._setup_branch_conflict(repo_path)
        with pytest.raises(subprocess.CalledProcessError):
            run_git(repo_path, ["merge", "other-branch"])

        with open(os.path.join(repo_path, "file.txt"), "w") as f:
            f.write("resolved version\n")
        run_git(repo_path, ["add", "file.txt"])

        assert manager.get_repository_state() == "MERGING"
        result = manager.continue_conflict_resolution()
        assert "Merge finalized" in result["message"]
        assert manager.get_repository_state() == "CLEAN"
        log_output = run_git(repo_path, ["log", "-1", "--pretty=%s"])
        assert "Merge branch 'other-branch'" in log_output

    def test_abort_conflict_resolution_aborts_rebase(self, manager_local):
        manager, repo_path = manager_local
        self._setup_branch_conflict(repo_path)
        run_git(repo_path, ["checkout", "other-branch"])
        with pytest.raises(subprocess.CalledProcessError):
            run_git(repo_path, ["rebase", TEST_BRANCH_MAIN])

        manager.abort_conflict_resolution()
        assert manager.get_repository_state() == "CLEAN"
        log_output = run_git(repo_path, ["log", "-1", "--pretty=%s"])
        assert log_output == "Base commit for branching"

    def test_continue_conflict_resolution_completes_rebase(self, manager_local):
        manager, repo_path = manager_local
        self._setup_branch_conflict(repo_path)
        run_git(repo_path, ["checkout", "other-branch"])
        with pytest.raises(subprocess.CalledProcessError):
            run_git(repo_path, ["rebase", TEST_BRANCH_MAIN])

        with open(os.path.join(repo_path, "file.txt"), "w") as f:
            f.write("resolved version\n")
        run_git(repo_path, ["add", "file.txt"])

        result = manager.continue_conflict_resolution()
        assert "Rebase finished" in result["message"]
        assert manager.get_repository_state() == "CLEAN"

    def test_continue_resolution_in_clean_state_raises_error(self, manager_local):
        manager, _ = manager_local
        with pytest.raises(GitManagerError):
            manager.continue_conflict_resolution()


class TestRemoteOperations:
    def test_push_succeeds_when_ahead(self, manager_with_remote):
        manager, local_path, remote_path = manager_with_remote
        with open(os.path.join(local_path, "local_change.txt"), "w") as f:
            f.write("local content")
        run_git(local_path, ["add", "."])
        run_git(local_path, ["commit", "-m", "Local commit"])
        manager.push_local_changes()
        remote_head_hash = run_git(remote_path, ["rev-parse", TEST_BRANCH_MAIN])
        remote_log_subject = run_git(
            remote_path, ["show", "-s", "--format=%s", remote_head_hash]
        )
        assert remote_log_subject == "Local commit"

    def test_pull_succeeds_when_behind(self, manager_with_remote):
        manager, local_path, remote_path = manager_with_remote
        # Simulate a remote change
        temp_clone_path = os.path.join(os.path.dirname(local_path), "temp_clone")
        run_git(os.path.dirname(local_path), ["clone", remote_path, temp_clone_path])
        with open(os.path.join(temp_clone_path, "remote_file.txt"), "w") as f:
            f.write("remote content")
        run_git(temp_clone_path, ["add", "."])
        run_git(temp_clone_path, ["commit", "-m", "Remote change"])
        run_git(temp_clone_path, ["push", "origin", TEST_BRANCH_MAIN])

        manager.pull_remote_changes()
        local_log = run_git(local_path, ["log", "-1", "--pretty=%s"])
        assert local_log == "Remote change"

    def test_sync_workspace_full_cycle(self, manager_with_remote):
        manager, local_path, remote_path = manager_with_remote

        # 1. Simulate remote change
        temp_clone_path = os.path.join(os.path.dirname(local_path), "temp_clone_sync")
        run_git(os.path.dirname(local_path), ["clone", remote_path, temp_clone_path])
        with open(os.path.join(temp_clone_path, "remote_sync.txt"), "w") as f:
            f.write("remote")
        run_git(temp_clone_path, ["add", "."])
        run_git(temp_clone_path, ["commit", "-m", "Remote for sync"])
        run_git(temp_clone_path, ["push", "origin", TEST_BRANCH_MAIN])

        # 2. Make local change and sync
        with open(os.path.join(local_path, "local_sync.txt"), "w") as f:
            f.write("local")
        sync_results = manager.sync_workspace("feat: Full sync operation")
        assert "hash" in sync_results["commit"]

        # 3. Verify remote state
        remote_log = run_git(remote_path, ["log", TEST_BRANCH_MAIN, "--pretty=%s"])
        assert "feat: Full sync operation" in remote_log
        assert "Remote for sync" in remote_log

    def test_reset_to_remote_discards_local_commits(self, manager_with_remote):
        manager, local_path, remote_path = manager_with_remote
        run_git(local_path, ["commit", "--allow-empty", "-m", "Local commit 1"])
        run_git(local_path, ["commit", "--allow-empty", "-m", "Local commit 2"])
        manager.reset_to_remote()
        local_log_after = run_git(local_path, ["log", "--oneline"])
        remote_log = run_git(remote_path, ["log", TEST_BRANCH_MAIN, "--oneline"])
        assert local_log_after == remote_log

    @pytest.mark.parametrize("strategy", [PullStrategy.MERGE, PullStrategy.REBASE])
    def test_pull_strategies_handle_divergence(self, manager_with_remote, strategy):
        manager, local_path, remote_path = manager_with_remote
        manager.pull_strategy = strategy

        # Create a non-conflicting divergence
        temp_clone_path = os.path.join(
            os.path.dirname(local_path), "temp_clone_diverge"
        )
        run_git(os.path.dirname(local_path), ["clone", remote_path, temp_clone_path])
        with open(os.path.join(temp_clone_path, "remote_file.txt"), "w") as f:
            f.write("remote content")
        run_git(temp_clone_path, ["add", "."])
        run_git(temp_clone_path, ["commit", "-m", "Remote change"])
        run_git(temp_clone_path, ["push", "origin", TEST_BRANCH_MAIN])

        with open(os.path.join(local_path, "local_file.txt"), "w") as f:
            f.write("local divergent content")
        run_git(local_path, ["add", "."])
        run_git(local_path, ["commit", "-m", "Local divergent change"])

        manager.pull_remote_changes()

        if strategy == PullStrategy.MERGE:
            local_log = run_git(local_path, ["log", "-1", "--pretty=%s"])
            assert "Merge branch" in local_log
        else:  # REBASE
            local_log = run_git(local_path, ["log", "--oneline", "-n", "2"])
            assert "Local divergent change" in local_log
            assert "Remote change" in local_log
            assert local_log.find("Local divergent change") < local_log.find(
                "Remote change"
            )

    def test_push_non_fast_forward_raises_push_rejected_error(
        self, manager_with_remote
    ):
        manager, local_path, remote_path = manager_with_remote
        _setup_conflict_scenario(local_path, remote_path)  # This sets up divergence
        with pytest.raises(PushRejectedError):
            manager.push_local_changes()

    def test_rebase_continue_uses_configured_author(self, manager_with_remote):
        """
        Tests that a commit created by `rebase --continue` via subprocess
        uses the author and committer information configured in the GitManager instance.
        """
        manager, local_path, remote_path = manager_with_remote

        # 1. Setup a conflict scenario
        # Simulate a remote change
        temp_clone_path = os.path.join(os.path.dirname(local_path), "temp_clone")
        run_git(os.path.dirname(local_path), ["clone", remote_path, temp_clone_path])
        with open(os.path.join(temp_clone_path, "conflict_file.txt"), "w") as f:
            f.write("Remote content")
        run_git(temp_clone_path, ["add", "."])
        # The user info for this remote commit is set by the fixture's git config
        run_git(temp_clone_path, ["commit", "-m", "Remote change"])
        run_git(temp_clone_path, ["push", "origin", TEST_BRANCH_MAIN])

        # Create a conflicting local commit USING THE MANAGER
        # This ensures the original commit's author is from the manager's config.
        with open(os.path.join(local_path, "conflict_file.txt"), "w") as f:
            f.write("Local content")
        manager.add_file("conflict_file.txt")
        original_commit_details = manager.commit("Local change")
        assert original_commit_details is not None

        # 2. Trigger the rebase conflict
        with pytest.raises(MergeConflictError):
            manager.pull_remote_changes()
        assert manager.get_repository_state() == "REBASING_CONFLICT"

        # 3. Resolve the conflict and continue
        with open(os.path.join(local_path, "conflict_file.txt"), "w") as f:
            f.write("Resolved content")
        manager.add_file("conflict_file.txt")

        # This calls `_run_git_command`, which should apply our fix.
        manager.continue_conflict_resolution()

        # 4. Assert the author and committer of the rebased commit are correct
        last_commit_author_name = run_git(local_path, ["log", "-1", "--format=%an"])
        last_commit_committer_name = run_git(local_path, ["log", "-1", "--format=%cn"])

        # The author from the original commit should be preserved.
        assert last_commit_author_name == TEST_USER_NAME

        # The committer MUST be the one from the manager instance, proving our fix works.
        assert last_commit_committer_name == TEST_USER_NAME


class TestReadOnlyOperations:
    def test_get_commit_log_returns_commits(self, manager_local):
        manager, repo_path = manager_local
        run_git(repo_path, ["commit", "--allow-empty", "-m", "Second Commit"])
        run_git(repo_path, ["commit", "--allow-empty", "-m", "Third Commit"])
        log_entries = manager.get_commit_log(limit=5)
        assert len(log_entries) == 3
        assert log_entries[0]["message"] == "Third Commit"
        assert log_entries[1]["message"] == "Second Commit"

    def test_get_files_in_commit_returns_correct_files(self, manager_local):
        manager, repo_path = manager_local
        with open(os.path.join(repo_path, "note1.md"), "w") as f:
            f.write("a")
        with open(os.path.join(repo_path, "note2.md"), "w") as f:
            f.write("b")
        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "-m", "Add two notes"])
        commit_hash = run_git(repo_path, ["rev-parse", "HEAD"])
        files = manager.get_files_in_commit(commit_hash)
        assert len(files) == 3
        paths = {f["path"] for f in files}
        assert paths == {"note1.md", "note2.md", ".gitignore"}

    def test_get_files_in_initial_commit(self, manager_local):
        manager, repo_path = manager_local
        run_git(repo_path, ["add", ".gitignore"])
        run_git(repo_path, ["commit", "--amend", "-m", "Initial commit with file"])
        first_commit_hash = run_git(repo_path, ["rev-list", "--max-parents=0", "HEAD"])
        files = manager.get_files_in_commit(first_commit_hash)
        assert len(files) == 1
        assert files[0]["path"] == ".gitignore"

    def test_get_files_in_commit_with_invalid_hash(self, manager_local):
        manager, _ = manager_local
        with pytest.raises(GitError):
            manager.get_files_in_commit("a" * 40)

    def test_list_branches_returns_local_and_remote(self, manager_with_remote):
        manager, local_path, remote_path = manager_with_remote
        run_git(local_path, ["checkout", "-b", "local-feature"])

        temp_clone_path = os.path.join(os.path.dirname(local_path), "temp_clone")
        run_git(os.path.dirname(local_path), ["clone", remote_path, temp_clone_path])
        run_git(temp_clone_path, ["checkout", "-b", "remote-feature"])
        run_git(temp_clone_path, ["commit", "--allow-empty", "-m", "feat on remote"])
        run_git(temp_clone_path, ["push", "origin", "remote-feature"])

        branch_info = manager.fetch_and_list_branches()
        branch_names = {b["name"] for b in branch_info["branches"]}
        assert {"main", "local-feature", "remote-feature"}.issubset(branch_names)

    def test_switch_branch_changes_head(self, manager_with_remote):
        manager, local_path, _ = manager_with_remote
        run_git(local_path, ["checkout", "-b", "new-feature"])
        manager.switch_branch(TEST_BRANCH_MAIN)
        current_branch_after = run_git(local_path, ["branch", "--show-current"])
        assert current_branch_after == TEST_BRANCH_MAIN

    def test_switch_to_non_existent_branch_raises_error(self, manager_local):
        manager, _ = manager_local  # Unpack to match the fixture's return signature
        with pytest.raises(BranchNotFoundError):
            manager.switch_branch("non-existent-branch")

    def test_get_files_in_commit_returns_correct_statuses_for_amd(self, manager_local):
        """
        Regression test: Ensures that added, modified, and deleted files in a
        commit have the correct 'A', 'M', and 'D' statuses respectively.
        This verifies the diff direction is correct (parent -> commit).
        """
        manager, repo_path = manager_local

        # --- 1. Setup: Create the base commit ---
        path_to_modify = os.path.join(repo_path, "file-to-modify.md")
        path_to_delete = os.path.join(repo_path, "file-to-delete.md")

        with open(path_to_modify, "w") as f:
            f.write("Initial content")
        with open(path_to_delete, "w") as f:
            f.write("This file will be deleted")

        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "-m", "Base state for AMD test"])

        # --- 2. Setup: Create the target commit with A, M, and D changes ---
        # Add a new file
        with open(os.path.join(repo_path, "new-file.md"), "w") as f:
            f.write("This is a new file")
        run_git(repo_path, ["add", "new-file.md"])

        # Modify an existing file
        with open(path_to_modify, "w") as f:
            f.write("Modified content")
        run_git(repo_path, ["add", path_to_modify])

        # Delete a file
        os.remove(path_to_delete)
        run_git(repo_path, ["rm", "file-to-delete.md"])

        run_git(repo_path, ["commit", "-m", "Test commit with A, M, D changes"])
        target_commit_hash = run_git(repo_path, ["rev-parse", "HEAD"])

        # --- 3. Act: Get the files from the manager ---
        files_in_commit = manager.get_files_in_commit(target_commit_hash)

        # --- 4. Assert: Check the status of each file ---
        # For easier assertion, convert the list of dicts to a dict of path -> status
        statuses = {f["path"]: f["status"] for f in files_in_commit}

        assert "new-file.md" in statuses
        assert statuses["new-file.md"] == "A", "Newly created file should be 'A'"

        assert "file-to-modify.md" in statuses
        assert statuses["file-to-modify.md"] == "M", "Modified file should be 'M'"

        assert "file-to-delete.md" in statuses
        assert statuses["file-to-delete.md"] == "D", "Deleted file should be 'D'"

        # Also assert the total number of changes
        assert len(files_in_commit) == 3
