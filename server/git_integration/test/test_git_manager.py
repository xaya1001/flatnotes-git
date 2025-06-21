# server/git_integration/test/test_git_manager.py

import os
import subprocess

import pytest
from pygit2 import GitError

from ..git_config import PullStrategy
from ..git_manager import (
    GitManager,
    GitManagerError,
    NoChangesError,
    PushRejectedError,
)

# --- Fixtures: Test Setup Utilities ---


@pytest.fixture
def manager_and_path(tmp_path):
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True
    )

    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Initial empty commit"],
        cwd=repo_path,
        check=True,
    )
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo_path, check=True)

    manager = GitManager(
        repo_path=str(repo_path),
        default_branch="main",
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name="Test User",
        user_email="test@example.com",
    )
    return manager, str(repo_path)


@pytest.fixture
def repo_with_remote(tmp_path):
    local_repo_path = tmp_path / "local_repo"
    remote_repo_path = tmp_path / "remote_repo.git"

    subprocess.run(["git", "init", "--bare", str(remote_repo_path)], check=True)
    subprocess.run(
        ["git", "clone", str(remote_repo_path), str(local_repo_path)], check=True
    )

    local_path_str = str(local_repo_path)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=local_path_str, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=local_path_str,
        check=True,
    )

    subprocess.run(["git", "checkout", "-b", "main"], cwd=local_path_str, check=True)
    with open(os.path.join(local_path_str, "README.md"), "w") as f:
        f.write("# Test Repository\n")
    subprocess.run(["git", "add", "README.md"], cwd=local_path_str, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=local_path_str, check=True
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"], cwd=local_path_str, check=True
    )

    manager = GitManager(
        repo_path=local_path_str,
        default_branch="main",
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name="Test User",
        user_email="test@example.com",
    )
    return manager, local_path_str, str(remote_repo_path)


# --- Helper Function ---


def run_git(repo_path, command):
    result = subprocess.run(
        ["git"] + command, cwd=repo_path, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


# --- Test Classes ---


class TestInitialization:
    def test_initialization_creates_gitignore(self, manager_and_path):
        manager, repo_path = manager_and_path
        gitignore_path = os.path.join(repo_path, ".gitignore")
        assert os.path.exists(gitignore_path)
        with open(gitignore_path, "r") as f:
            assert ".flatnotes/" in f.read()


class TestCommit:
    def test_commit_no_staged_changes_raises_error(self, manager_and_path):
        manager, _ = manager_and_path
        with pytest.raises(NoChangesError):
            manager.commit("This should fail")

    def test_commit_with_staged_files_succeeds(self, manager_and_path):
        manager, repo_path = manager_and_path
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
    def test_add_all_stages_all_new_files(self, manager_and_path):
        manager, repo_path = manager_and_path
        with open(os.path.join(repo_path, "file1.md"), "w") as f:
            f.write("1")
        with open(os.path.join(repo_path, "file2.md"), "w") as f:
            f.write("2")
        manager.add_all()
        status_output = run_git(repo_path, ["status", "--porcelain"])
        assert "A  .gitignore" in status_output
        assert "A  file1.md" in status_output
        assert "A  file2.md" in status_output

    def test_unstage_file_moves_it_from_index_to_workspace(self, manager_and_path):
        manager, repo_path = manager_and_path
        file_path = "staged_file.md"
        with open(os.path.join(repo_path, file_path), "w") as f:
            f.write("content")
        run_git(repo_path, ["add", file_path])
        status_before = run_git(repo_path, ["status", "--porcelain"])
        assert f"A  {file_path}" in status_before.splitlines()
        manager.unstage_file(file_path)
        status_after = run_git(repo_path, ["status", "--porcelain"])
        assert f"?? {file_path}" in status_after.splitlines()

    def test_discard_file_removes_untracked_file(self, manager_and_path):
        manager, repo_path = manager_and_path
        file_path = os.path.join(repo_path, "untracked.md")
        with open(file_path, "w") as f:
            f.write("delete me")
        assert os.path.exists(file_path)
        manager.discard_file("untracked.md")
        assert not os.path.exists(file_path)

    def test_discard_all_cleans_workspace(self, manager_and_path):
        manager, repo_path = manager_and_path
        run_git(repo_path, ["add", ".gitignore"])
        run_git(repo_path, ["commit", "-m", "Initial"])
        with open(os.path.join(repo_path, ".gitignore"), "a") as f:
            f.write("\n# modified")
        with open(os.path.join(repo_path, "new_file.md"), "w") as f:
            f.write("new")
        manager.discard_all()
        status_output_after = run_git(repo_path, ["status", "--porcelain"])
        assert status_output_after == ""

    def test_checkout_file_from_commit_restores_file(self, manager_and_path):
        manager, repo_path = manager_and_path
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

    def test_checkout_invalid_commit_raises_error(self, manager_and_path):
        manager, _ = manager_and_path
        with pytest.raises(GitError):
            manager.checkout_file_from_commit("a" * 40, "anyfile.txt")


class TestRepositoryState:
    def _setup_conflict_scenario(self, repo_path):
        with open(os.path.join(repo_path, "file.txt"), "w") as f:
            f.write("initial version\n")
        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "--amend", "-m", "Initial commit"])
        run_git(repo_path, ["checkout", "-b", "other"])
        with open(os.path.join(repo_path, "file.txt"), "a") as f:
            f.write("change from other\n")
        run_git(repo_path, ["commit", "-am", "Commit on other"])
        run_git(repo_path, ["checkout", "main"])
        with open(os.path.join(repo_path, "file.txt"), "a") as f:
            f.write("change from main\n")
        run_git(repo_path, ["commit", "-am", "Commit on main"])

    def test_get_repository_state_merge_conflict(self, manager_and_path):
        manager, repo_path = manager_and_path
        self._setup_conflict_scenario(repo_path)
        try:
            subprocess.run(
                ["git", "merge", "other"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            pass
        state = manager.get_repository_state()
        assert state == "MERGING_CONFLICT"
        assert "file.txt" in manager.get_conflicted_files()

    def test_get_repository_state_rebase_conflict(self, manager_and_path):
        manager, repo_path = manager_and_path
        self._setup_conflict_scenario(repo_path)
        run_git(repo_path, ["checkout", "other"])
        try:
            subprocess.run(
                ["git", "rebase", "main"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            pass
        state = manager.get_repository_state()
        assert state == "REBASING_CONFLICT"
        assert "file.txt" in manager.get_conflicted_files()

    def test_abort_conflict_resolution_aborts_merge(self, manager_and_path):
        manager, repo_path = manager_and_path
        self._setup_conflict_scenario(repo_path)
        try:
            subprocess.run(
                ["git", "merge", "other"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            pass
        manager.abort_conflict_resolution()
        assert manager.get_repository_state() == "CLEAN"
        status_output = run_git(repo_path, ["status", "--porcelain"])
        assert "M  file.txt" in status_output

    def test_continue_conflict_resolution_completes_merge(self, manager_and_path):
        manager, repo_path = manager_and_path
        self._setup_conflict_scenario(repo_path)
        try:
            subprocess.run(
                ["git", "merge", "other"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            pass
        with open(os.path.join(repo_path, "file.txt"), "w") as f:
            f.write("resolved version\n")
        run_git(repo_path, ["add", "file.txt"])
        assert manager.get_repository_state() == "MERGING"
        result = manager.continue_conflict_resolution()
        assert "Merge finalized" in result["message"]
        assert manager.get_repository_state() == "CLEAN"
        log_output = run_git(repo_path, ["log", "-1", "--pretty=%s"])
        assert "Merge branch 'other'" in log_output

    def test_continue_resolution_in_clean_state_raises_error(self, manager_and_path):
        manager, _ = manager_and_path
        with pytest.raises(GitManagerError):
            manager.continue_conflict_resolution()


class TestRemoteOperations:
    def test_push_succeeds_when_ahead(self, repo_with_remote):
        manager, local_path, remote_path = repo_with_remote
        with open(os.path.join(local_path, "local_change.txt"), "w") as f:
            f.write("local content")
        run_git(local_path, ["add", "."])
        run_git(local_path, ["commit", "-m", "Local commit"])
        manager.push_local_changes()
        remote_head_hash = run_git(remote_path, ["rev-parse", "main"])
        remote_log_subject = run_git(
            remote_path, ["show", "-s", "--format=%s", remote_head_hash]
        )
        assert remote_log_subject == "Local commit"

    def test_pull_succeeds_when_behind(self, repo_with_remote):
        manager, local_path, remote_path = repo_with_remote
        temp_clone_path = os.path.join(os.path.dirname(remote_path), "temp_clone")
        run_git(
            os.path.dirname(remote_path),
            ["clone", "-b", "main", remote_path, temp_clone_path],
        )
        run_git(temp_clone_path, ["config", "user.name", "Remote Actor"])
        run_git(temp_clone_path, ["config", "user.email", "remote@example.com"])
        with open(os.path.join(temp_clone_path, "remote_change.txt"), "w") as f:
            f.write("remote content")
        run_git(temp_clone_path, ["add", "."])
        run_git(temp_clone_path, ["commit", "-m", "Remote commit"])
        run_git(temp_clone_path, ["push", "origin", "main"])
        manager.pull_remote_changes()
        local_log = run_git(local_path, ["log", "-1", "--pretty=%s"])
        assert local_log == "Remote commit"

    def test_sync_workspace_full_cycle(self, repo_with_remote):
        manager, local_path, remote_path = repo_with_remote
        temp_clone_path = os.path.join(os.path.dirname(remote_path), "temp_clone_sync")
        run_git(
            os.path.dirname(remote_path),
            ["clone", "-b", "main", remote_path, temp_clone_path],
        )
        run_git(temp_clone_path, ["config", "user.name", "Remote Actor"])
        run_git(temp_clone_path, ["config", "user.email", "remote@example.com"])
        with open(os.path.join(temp_clone_path, "remote_sync.txt"), "w") as f:
            f.write("remote")
        run_git(temp_clone_path, ["add", "."])
        run_git(temp_clone_path, ["commit", "-m", "Remote for sync"])
        run_git(temp_clone_path, ["push", "origin", "main"])
        with open(os.path.join(local_path, "local_sync.txt"), "w") as f:
            f.write("local")
        sync_results = manager.sync_workspace("feat: Full sync operation")
        assert "hash" in sync_results["commit"]
        remote_log = run_git(remote_path, ["log", "main", "--pretty=%s"])
        assert "feat: Full sync operation" in remote_log
        assert "Remote for sync" in remote_log

    def test_reset_to_remote_discards_local_commits(self, repo_with_remote):
        manager, local_path, remote_path = repo_with_remote
        run_git(local_path, ["commit", "--allow-empty", "-m", "Local commit 1"])
        run_git(local_path, ["commit", "--allow-empty", "-m", "Local commit 2"])
        manager.reset_to_remote()
        local_log_after = run_git(local_path, ["log", "--oneline"])
        remote_log = run_git(remote_path, ["log", "main", "--oneline"])
        assert local_log_after == remote_log

    def test_pull_with_merge_strategy_creates_merge_commit(self, repo_with_remote):
        _, local_path, remote_path = repo_with_remote
        manager = GitManager(
            repo_path=local_path,
            default_branch="main",
            default_remote="origin",
            pull_strategy=PullStrategy.MERGE,
        )
        temp_clone_path = os.path.join(os.path.dirname(remote_path), "temp_clone_merge")
        run_git(
            os.path.dirname(remote_path),
            ["clone", "-b", "main", remote_path, temp_clone_path],
        )
        run_git(temp_clone_path, ["config", "user.name", "Remote Actor"])
        run_git(temp_clone_path, ["config", "user.email", "remote@example.com"])
        with open(os.path.join(temp_clone_path, "remote_file.txt"), "w") as f:
            f.write("r")
        run_git(temp_clone_path, ["add", "."])
        run_git(temp_clone_path, ["commit", "-m", "Remote change"])
        run_git(temp_clone_path, ["push", "origin", "main"])
        with open(os.path.join(local_path, "local_file.txt"), "w") as f:
            f.write("l")
        run_git(local_path, ["add", "."])
        run_git(local_path, ["commit", "-m", "Local change"])
        manager.pull_remote_changes()
        local_log = run_git(local_path, ["log", "-1", "--pretty=%s"])
        assert "Merge branch 'main' of" in local_log

    def test_push_non_fast_forward_raises_push_rejected_error(self, repo_with_remote):
        manager, local_path, remote_path = repo_with_remote
        with open(os.path.join(local_path, "local_file.txt"), "w") as f:
            f.write("l")
        run_git(local_path, ["add", "."])
        run_git(local_path, ["commit", "-m", "Local change"])
        temp_clone_path = os.path.join(os.path.dirname(remote_path), "temp_clone_ff")
        run_git(
            os.path.dirname(remote_path),
            ["clone", "-b", "main", remote_path, temp_clone_path],
        )
        run_git(temp_clone_path, ["config", "user.name", "Remote Actor"])
        run_git(temp_clone_path, ["config", "user.email", "remote@example.com"])
        with open(os.path.join(temp_clone_path, "remote_file.txt"), "w") as f:
            f.write("r")
        run_git(temp_clone_path, ["add", "."])
        run_git(temp_clone_path, ["commit", "-m", "Remote change"])
        run_git(temp_clone_path, ["push", "origin", "main"])
        with pytest.raises(PushRejectedError):
            manager.push_local_changes()


class TestReadOnlyOperations:
    def test_get_commit_log_returns_commits(self, manager_and_path):
        manager, repo_path = manager_and_path
        with open(os.path.join(repo_path, "file1.md"), "w") as f:
            f.write("1")
        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "-m", "Second Commit"])
        with open(os.path.join(repo_path, "file2.md"), "w") as f:
            f.write("2")
        run_git(repo_path, ["add", "."])
        run_git(repo_path, ["commit", "-m", "Third Commit"])
        log_entries = manager.get_commit_log(limit=5)
        assert len(log_entries) == 3
        assert log_entries[0]["message"] == "Third Commit"
        assert log_entries[1]["message"] == "Second Commit"
        assert log_entries[2]["message"] == "Initial empty commit"

    def test_get_files_in_commit_returns_correct_files(self, manager_and_path):
        manager, repo_path = manager_and_path
        with open(os.path.join(repo_path, "note1.md"), "w") as f:
            f.write("a")
        with open(os.path.join(repo_path, "note2.md"), "w") as f:
            f.write("b")
        run_git(repo_path, ["add", "note1.md", "note2.md"])
        run_git(repo_path, ["commit", "-m", "Add two notes"])
        commit_hash = run_git(repo_path, ["rev-parse", "HEAD"])
        files = manager.get_files_in_commit(commit_hash)
        assert len(files) == 2
        paths = {f["path"] for f in files}
        assert paths == {"note1.md", "note2.md"}

    def test_get_files_in_initial_commit(self, manager_and_path):
        manager, repo_path = manager_and_path
        run_git(repo_path, ["add", ".gitignore"])
        run_git(repo_path, ["commit", "--amend", "-m", "Initial commit with file"])
        first_commit_hash = run_git(repo_path, ["rev-list", "--max-parents=0", "HEAD"])
        files = manager.get_files_in_commit(first_commit_hash)
        assert len(files) == 1
        assert files[0]["path"] == ".gitignore"

    def test_list_branches_returns_local_and_remote(self, repo_with_remote):
        manager, local_path, remote_path = repo_with_remote
        run_git(local_path, ["checkout", "-b", "local-feature"])
        temp_clone_path = os.path.join(
            os.path.dirname(remote_path), "temp_clone_branch"
        )
        run_git(
            os.path.dirname(remote_path),
            ["clone", "-b", "main", remote_path, temp_clone_path],
        )
        run_git(temp_clone_path, ["checkout", "-b", "remote-feature"])
        run_git(temp_clone_path, ["commit", "--allow-empty", "-m", "feat on remote"])
        run_git(temp_clone_path, ["push", "origin", "remote-feature"])
        branch_info = manager.fetch_and_list_branches()
        branches = branch_info["branches"]
        branch_names = {b["name"] for b in branches}
        assert {"main", "local-feature", "remote-feature"}.issubset(branch_names)

    def test_switch_branch_changes_head(self, manager_and_path):
        manager, repo_path = manager_and_path
        run_git(repo_path, ["checkout", "-b", "new-feature"])
        manager.switch_branch("main")
        current_branch_after = run_git(repo_path, ["branch", "--show-current"])
        assert current_branch_after == "main"

    def test_switch_to_non_existent_branch_raises_error(self, manager_and_path):
        manager, _ = manager_and_path
        with pytest.raises(GitManagerError):
            manager.switch_branch("non-existent-branch")
