# server/git_integration/test/test_sync_workflow.py (FINAL, CORRECTED VERSION 2)

import os

import pygit2
import pytest

from ..git_manager import MergeConflictError

# Constants for this test file
TEMP_NOTE_REF = "refs/notes/flatnotes-sync"

# --- Helper function for this file ---


def create_remote_divergence(tmp_path, remote_path, conflicting=True):
    """
    Creates a new commit on the remote repository to cause a divergence.
    It does NOT touch the local repository.
    """
    clone_path = tmp_path / "remote_clone_for_divergence"
    remote_repo = pygit2.clone_repository(remote_path, str(clone_path))
    remote_author = pygit2.Signature("Remote User", "remote@example.com")

    if conflicting:
        # Modify a file that also exists locally to guarantee a conflict
        file_to_modify = "README.md"
        new_content = "# Remote Change\n"
    else:
        # Add a new file to avoid conflicts
        file_to_modify = "remote_file.md"
        new_content = "Remote content\n"

    with open(os.path.join(remote_repo.workdir, file_to_modify), "w") as f:
        f.write(new_content)

    remote_repo.index.add(file_to_modify)
    remote_repo.index.write()
    remote_repo.create_commit(
        "HEAD",
        remote_author,
        remote_author,
        "Remote divergence",
        remote_repo.index.write_tree(),
        [remote_repo.head.target],
    )
    remote_repo.remotes["origin"].push([f"refs/heads/{remote_repo.head.shorthand}"])


# --- Test Cases ---


def test_sync_successful_path_with_dirty_workspace(manager_with_remote):
    manager, repo, local_path, _ = manager_with_remote

    with open(os.path.join(local_path, "new_note.md"), "w") as f:
        f.write("This is a new note.")

    manager.commit_and_sync("feat: Add new note")

    with pytest.raises(KeyError):
        repo.lookup_reference(TEMP_NOTE_REF)

    last_commit = repo.head.peel()
    assert last_commit.message.strip() == "feat: Add new note"


def test_conflict_and_abort_with_dirty_workspace(tmp_path, manager_with_remote):
    manager, repo, local_path, remote_path = manager_with_remote

    # 1. Create a conflicting commit on the remote
    create_remote_divergence(tmp_path, remote_path, conflicting=True)

    # 2. Make local changes to the *same file* and other files
    with open(os.path.join(local_path, "README.md"), "w") as f:
        f.write("# Local Conflicting Change\n")
    with open(os.path.join(local_path, "local_file.md"), "w") as f:
        f.write("Some other work\n")

    original_head_hash = str(repo.head.target)

    # 3. Trigger the sync, which will create a temp commit and then conflict
    with pytest.raises(MergeConflictError):
        manager.commit_and_sync("feat: This will conflict")

    # 4. Abort the conflict
    result = manager.abort_conflict_resolution()

    # 5. Assert the outcome
    assert "temporary sync commit has been undone" in result

    # The HEAD should have reverted to the commit that existed before the sync
    assert str(repo.head.target) == original_head_hash

    # After a soft reset, the changes should be in the STAGING area.
    status = repo.status()
    assert "README.md" in status
    assert "local_file.md" in status
    assert status["README.md"] == pygit2.GIT_STATUS_INDEX_MODIFIED
    assert status["local_file.md"] == pygit2.GIT_STATUS_INDEX_NEW

    # The temp note ref MUST be gone
    with pytest.raises(KeyError):
        repo.lookup_reference(TEMP_NOTE_REF)


def test_conflict_and_abort_with_clean_workspace(tmp_path, manager_with_remote):
    manager, repo, local_path, remote_path = manager_with_remote

    # 1. Create a legitimate local commit that will conflict
    with open(os.path.join(local_path, "README.md"), "w") as f:
        f.write("# My Legitimate Local Change\n")
    manager.add_all()
    user_commit_hash = manager.commit("feat: My legitimate commit")["hash"]

    # 2. Create a conflicting commit on the remote
    create_remote_divergence(tmp_path, remote_path, conflicting=True)

    # 3. Trigger the sync. Workspace is clean, so it will directly pull and conflict.
    with pytest.raises(MergeConflictError):
        manager.commit_and_sync("This message is ignored")

    # 4. Abort the conflict
    result = manager.abort_conflict_resolution()

    # 5. Assert the outcome
    assert "Your commit history is untouched" in result
    assert str(repo.head.target) == user_commit_hash
    assert not repo.status()
    with pytest.raises(KeyError):
        repo.lookup_reference(TEMP_NOTE_REF)


def test_conflict_and_continue_workflow(tmp_path, manager_with_remote):
    manager, repo, local_path, remote_path = manager_with_remote

    create_remote_divergence(tmp_path, remote_path, conflicting=True)

    with open(os.path.join(local_path, "README.md"), "w") as f:
        f.write("# Local Conflicting Change\n")

    with pytest.raises(MergeConflictError):
        manager.commit_and_sync("feat: Sync with conflict")

    # Manually resolve the conflict
    with open(os.path.join(repo.workdir, "README.md"), "w") as f:
        f.write("# Resolved Content\n")
    manager.add_file("README.md")

    manager.continue_conflict_resolution()

    assert manager.get_repository_state() == "CLEAN"

    with pytest.raises(KeyError):
        repo.lookup_reference(TEMP_NOTE_REF)

    log = list(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL))
    assert log[0].message.strip() == "feat: Sync with conflict"
    assert log[1].message.strip() == "Remote divergence"


def test_sync_when_only_ahead_succeeds_without_error(manager_with_remote, run_git):
    """
    Tests the specific bug fix: when local is ahead of remote but not behind,
    commit_and_sync should succeed without trying an unnecessary and failing pull.
    """
    manager, repo, local_path, remote_path = manager_with_remote

    # 1. Capture the remote state before we make local changes.
    remote_head_before = run_git(remote_path, ["rev-parse", "HEAD"])

    # 2. Create a new local commit, making the local repo 1 commit ahead.
    with open(os.path.join(local_path, "new_file_for_test.md"), "w") as f:
        f.write("This is a new local-only file.")

    # 3. Execute commit_and_sync. THIS IS THE ACTION WE ARE TESTING.
    # We expect this to run without raising any exceptions.
    try:
        sync_result = manager.commit_and_sync("feat: Add a new file locally")
    except Exception as e:
        pytest.fail(f"commit_and_sync raised an unexpected exception: {e}")

    # 4. Assertions
    # The pull step should have been skipped.
    assert "Pull skipped" in sync_result["pull"]["message"]

    # The push step should have been successful.
    assert "Push successful" in sync_result["push"]["message"]
    assert sync_result["push"]["commits_pushed"] == 1

    # The remote repository should now have our new commit.
    remote_head_after = run_git(remote_path, ["rev-parse", "HEAD"])
    assert remote_head_after != remote_head_before

    remote_log = run_git(remote_path, ["log", "-1", "--pretty=%s"])
    assert remote_log == "feat: Add a new file locally"

    # The temporary note ref MUST be gone.
    with pytest.raises(KeyError):
        repo.lookup_reference(TEMP_NOTE_REF)

    # The local repository should be clean.
    assert not repo.status()
