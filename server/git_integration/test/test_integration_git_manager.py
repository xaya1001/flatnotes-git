# server/git_integration/test/test_integration_git_manager.py

from pathlib import Path

import pygit2
import pytest

from git_integration.test.conftest import make_commit

from ..git_manager import GitManager, MergeConflictError


def test_fetch_only(git_manager: GitManager, second_clone_repo: pygit2.Repository):
    """
    Tests that fetch_only updates the remote-tracking branch.
    """
    # 1. Make and push a commit from the second clone to simulate a remote change
    make_commit(second_clone_repo, "remote_file.md", "from remote", "Add remote file")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. Check that local remote branch is behind before fetch
    local_main_ref = git_manager.repo.lookup_reference("refs/heads/main")
    remote_tracking_ref = git_manager.repo.lookup_reference("refs/remotes/origin/main")
    assert local_main_ref.target == remote_tracking_ref.target

    # 3. Act
    git_manager.fetch_only()

    # 4. Assert: The remote-tracking branch should now be ahead
    new_remote_tracking_ref = git_manager.repo.lookup_reference(
        "refs/remotes/origin/main"
    )
    assert local_main_ref.target != new_remote_tracking_ref.target
    assert git_manager.repo.descendant_of(
        new_remote_tracking_ref.target, local_main_ref.target
    )


def test_push_local_changes(git_manager: GitManager):
    """
    Tests pushing a local commit to the remote.
    """
    # 1. Arrange: Make a local commit
    local_commit_oid = make_commit(
        git_manager.repo, "local_file.md", "local content", "Add local file"
    )

    # 2. Act: Push the changes
    result = git_manager.push_local_changes()

    # 3. Assert
    assert result["message"] == "Push successful."
    assert result["commits_pushed"] == 1
    assert result["commits"][0]["hash"] == str(local_commit_oid)

    # Verify the commit exists on the remote by checking the branch ref
    remote_repo = pygit2.Repository(git_manager.get_remote_url())
    remote_main_ref = remote_repo.references["refs/heads/main"]
    assert str(remote_main_ref.target) == str(local_commit_oid)


def test_pull_remote_changes_fast_forward(
    git_manager: GitManager, second_clone_repo: pygit2.Repository
):
    """
    Tests a simple pull (fast-forward) scenario.
    """
    # 1. Arrange: Make and push a commit from the second clone
    remote_commit_oid = make_commit(
        second_clone_repo, "from_remote.md", "content", "Commit from remote"
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. Act: Pull changes
    result = git_manager.pull_remote_changes()

    # 3. Assert
    assert "Pull successful" in result["message"]
    assert result["commits_received"] > 0

    # Verify the local HEAD is now at the remote commit
    local_head = git_manager.repo.head.peel()
    assert str(local_head.id) == str(remote_commit_oid)
    assert (Path(git_manager.repo.workdir) / "from_remote.md").exists()


def test_commit_and_sync_with_dirty_workspace(git_manager: GitManager):
    """
    Tests the full commit_and_sync workflow starting with a dirty workspace.
    """
    # 1. Arrange: Dirty the workspace
    (Path(git_manager.repo.workdir) / "sync_test.md").write_text("sync me")

    # 2. Act: Run the sync process
    result = git_manager.commit_and_sync("feat: Add sync test file")

    # 3. Assert
    assert "commit" in result
    assert "pull" in result
    assert "push" in result
    assert result["commit"]["message"] == "feat: Add sync test file"
    assert "Push successful" in result["push"]["message"]

    # Verify remote has the commit
    remote_repo = pygit2.Repository(git_manager.get_remote_url())
    remote_head_commit = remote_repo.references["refs/heads/main"].peel()
    assert remote_head_commit.message.strip() == "feat: Add sync test file"
    assert "sync_test.md" in remote_head_commit.tree


def test_pull_causes_merge_conflict(
    git_manager: GitManager, second_clone_repo: pygit2.Repository
):
    """
    Tests that a pull operation correctly identifies and raises a merge conflict.
    """
    # 1. Arrange: Create divergent histories from the common ancestor.
    # Local change
    make_commit(
        git_manager.repo,
        "README.md",
        "Local change on README",
        "docs: Update README locally",
    )

    # Remote change on the same file, created in the second clone
    make_commit(
        second_clone_repo,
        "README.md",
        "Remote change on README",
        "docs: Update README remotely",
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. Act & Assert: The pull should now fail with a conflict
    with pytest.raises(MergeConflictError):
        git_manager.pull_remote_changes()

    # Assert repo state
    assert git_manager.get_repository_state() == "REBASING_CONFLICT"
    assert "README.md" in git_manager.get_conflicted_files()

    # 3. Abort the resolution
    abort_message = git_manager.abort_conflict_resolution()
    assert "aborted" in abort_message
    assert git_manager.get_repository_state() == "CLEAN"
    assert not git_manager.get_conflicted_files()
