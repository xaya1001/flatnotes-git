# server/git_integration/test/test_edge_cases_git_manager.py

from pathlib import Path

import pygit2
import pytest
from pygit2.enums import FileStatus

from git_integration.test.conftest import make_commit

from ..git_manager import (
    BranchNotFoundError,
    GitManager,
    GitManagerError,
    MergeConflictError,
    PushRejectedError,
)

# --- Edge Case Tests ---


def test_commit_and_sync_on_clean_workspace(git_manager: GitManager):
    """
    Tests that commit_and_sync on a clean workspace skips the commit
    and proceeds directly to pull/push.
    """
    # Arrange: Workspace is clean by default from the fixture.

    # Act
    result = git_manager.commit_and_sync("This message should not be used")

    # Assert
    assert "Workspace is clean" in result["commit"]["message"]
    assert "Already up-to-date" in result["pull"]["message"]
    assert "Nothing to push" in result["push"]["message"]


def test_push_to_diverged_remote_raises_push_rejected_error(
    git_manager: GitManager, second_clone_repo: pygit2.Repository
):
    """
    Tests that a push is rejected with PushRejectedError if the remote has
    divergent changes (non-fast-forward).
    """
    # Arrange:
    # 1. FIX: Use the 'second_clone_repo' to simulate a remote commit.
    # This repository has a working directory and can create commits normally.
    # Then, push the change to the bare 'origin' repository.
    make_commit(second_clone_repo, "remote_only.md", "divergent", "A commit on remote")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. Create a different commit locally in the main test repository.
    make_commit(git_manager.repo, "local_only.md", "local", "A commit on local")

    # Act & Assert
    with pytest.raises(PushRejectedError):
        git_manager.push_local_changes()


def test_operations_in_detached_head_state_fail(git_manager: GitManager):
    """
    Tests that critical sync operations fail when in a detached HEAD state.
    """
    # Arrange: Detach the HEAD by checking out a commit hash directly.
    head_hash = git_manager.repo.head.target
    git_manager.repo.set_head(head_hash)
    assert git_manager.repo.head_is_detached

    # Act & Assert
    with pytest.raises(GitManagerError, match="Cannot push in a detached HEAD state"):
        git_manager.push_local_changes()

    with pytest.raises(GitManagerError, match="Cannot pull in a detached HEAD state"):
        git_manager.pull_remote_changes()


def test_pull_with_merge_strategy_creates_merge_commit(
    git_manager_merge_strategy: GitManager, second_clone_repo: pygit2.Repository
):
    """
    Tests that using the MERGE pull strategy correctly creates a merge commit
    when histories have diverged.
    """
    manager = git_manager_merge_strategy

    # Arrange: Create divergent histories
    # 1. FIX: Use 'second_clone_repo' to create and push a remote commit.
    make_commit(second_clone_repo, "remote_file.md", "", "Remote commit")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. Local commit
    make_commit(manager.repo, "local_file.md", "", "Local commit")

    # Act
    manager.pull_remote_changes()

    # Assert: The new HEAD commit must be a merge commit (i.e., have 2 parents)
    new_head = manager.repo.head.peel()
    assert len(new_head.parents) == 2
    assert manager.get_repository_state() == "CLEAN"


def test_continue_rebase_after_resolving_conflict(
    git_manager: GitManager, second_clone_repo: pygit2.Repository
):
    """
    Tests the full conflict resolution workflow:
    1. Trigger a conflict by creating divergent histories on the same file.
    2. Manually resolve it.
    3. Call continue_conflict_resolution.
    """
    # Arrange: Create a rebase conflict
    # FIX: Create a proper conflict scenario from a common ancestor.
    # The initial commit on README.md is our common ancestor.

    # 1. Create a local commit modifying README.md
    make_commit(git_manager.repo, "README.md", "Local change to README", "Local")

    # 2. Create a remote commit modifying the same file and push it
    make_commit(second_clone_repo, "README.md", "Remote change to README", "Remote")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # Act 1: Trigger the conflict by pulling. Rebase will fail.
    with pytest.raises(MergeConflictError):
        git_manager.pull_remote_changes()

    assert git_manager.get_repository_state() == "REBASING_CONFLICT"

    # Act 2: Manually resolve the conflict
    conflict_file_path = Path(git_manager.repo.workdir) / "README.md"
    conflict_file_path.write_text("Resolved change to README")
    git_manager.add_file("README.md")
    assert (
        git_manager.get_repository_state() == "REBASING_CONTINUE"
    )  # State changes after staging

    # Act 3: Continue the rebase and push
    result = git_manager.continue_conflict_resolution()

    # Assert
    assert "Rebase finished and pushed successfully" in result["message"]
    assert git_manager.get_repository_state() == "CLEAN"

    # Verify the remote has the final resolved commit by checking from the second clone
    second_clone_repo.remotes["origin"].fetch()
    second_clone_repo.reset(
        second_clone_repo.branches["origin/main"].target, pygit2.GIT_RESET_HARD
    )
    final_remote_content = (Path(second_clone_repo.workdir) / "README.md").read_text()
    assert "Resolved change to README" in final_remote_content


def test_abort_conflict_with_temp_commit_resets_it(
    git_manager: GitManager, second_clone_repo: pygit2.Repository
):
    """
    This is a critical test for the sync-with-dirty-workspace feature.
    It ensures that if a sync operation creates a temporary commit and then fails,
    aborting the operation correctly removes that temporary commit.
    """
    # Arrange 1: Create a conflicting change on the remote.
    make_commit(
        second_clone_repo,
        "README.md",
        "Remote change that will conflict",
        "Remote conflict commit",
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # Arrange 2: Dirty the local workspace and record the state before sync.
    (Path(git_manager.repo.workdir) / "README.md").write_text(
        "My temporary local change"
    )
    original_head_oid = git_manager.repo.head.target

    # Act 1: Run commit_and_sync, which we expect to fail with a conflict.
    with pytest.raises(MergeConflictError):
        git_manager.commit_and_sync("temp sync commit")

    # Assert 1: The repository is in a conflict state.
    assert "CONFLICT" in git_manager.get_repository_state()

    # Get the OID of the temporary commit that was created.
    # The reflog is the most reliable source for this. The last entry for HEAD
    # before the rebase started will be our temporary commit.
    # FIX: Convert the RefLogIter iterator to a list before accessing by index.
    reflog_entries = list(git_manager.repo.head.log())
    # The log entries are newest first.
    # Entry 0: rebase start
    # Entry 1: our temporary commit
    assert (
        len(reflog_entries) >= 2
    ), "Reflog should contain at least the temp commit and rebase start entries"
    temp_commit_oid = reflog_entries[1].oid_new
    assert git_manager.repo.get(temp_commit_oid).message.strip() == "temp sync commit"

    # Act 2: Abort the resolution. This is the core logic we are testing.
    result_message = git_manager.abort_conflict_resolution()

    # Assert 2: The operation is aborted, and the temporary commit is undone.
    assert "temporary sync commit has been undone" in result_message

    # The HEAD should be back to where it was before we started the sync.
    assert git_manager.repo.head.target == original_head_oid

    # The note that was on the temporary commit should now be gone.
    # The `_cleanup_temp_notes` method should have removed the entire ref.
    assert git_manager.repo.references.get("refs/notes/flatnotes-sync") is None

    # The user's changes should be preserved in the staging area.
    status = git_manager.repo.status()
    assert status["README.md"] == FileStatus.INDEX_MODIFIED
    assert (
        "My temporary local change"
        in (Path(git_manager.repo.workdir) / "README.md").read_text()
    )


def test_switch_to_non_existent_branch_fails(git_manager: GitManager):
    """
    Tests that switching to a branch that does not exist locally or on the
    remote raises BranchNotFoundError.
    """
    with pytest.raises(BranchNotFoundError):
        git_manager.switch_branch("non-existent-branch-12345")


def test_sync_when_ahead_and_clean_only_pushes(git_manager: GitManager):
    """
    Tests that commit_and_sync on a clean, but ahead, workspace only performs a push.
    """
    # Arrange: Make local ahead of remote
    make_commit(git_manager.repo, "local_ahead.md", "", "feat: new feature")
    assert git_manager.get_status()["commits_ahead"] == 1

    # Act
    result = git_manager.commit_and_sync("This message should not be used")

    # Assert
    assert "Workspace is clean" in result["commit"]["message"]
    assert "Already up-to-date" in result["pull"]["message"]
    assert "Push successful" in result["push"]["message"]
    assert result["push"]["commits_pushed"] == 1


def test_continue_in_clean_state_raises_error(git_manager: GitManager):
    """
    Tests that calling continue_conflict_resolution when not in a conflict
    state raises a specific error.
    """
    assert git_manager.get_repository_state() == "CLEAN"
    with pytest.raises(GitManagerError, match="No conflict resolution to continue"):
        git_manager.continue_conflict_resolution()


def test_merge_conflict_and_resolution_workflow(
    git_manager_merge_strategy: GitManager, second_clone_repo: pygit2.Repository
):
    """
    Tests the full MERGE conflict workflow: trigger, check state, resolve, and continue.
    """
    manager = git_manager_merge_strategy

    # FIX: Create a conflict on an existing file (README.md) to avoid add/add.
    # 1. Local commit
    make_commit(
        manager.repo, "README.md", "local change to readme", "docs: Local update"
    )

    # 2. Remote commit on the same file
    make_commit(
        second_clone_repo, "README.md", "remote change to readme", "docs: Remote update"
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # Act 1: Trigger conflict
    with pytest.raises(MergeConflictError):
        manager.pull_remote_changes()

    # Assert 1: State is MERGING_CONFLICT
    assert manager.get_repository_state() == "MERGING_CONFLICT"
    assert "README.md" in manager.get_conflicted_files()

    # Act 2: Resolve conflict
    (Path(manager.repo.workdir) / "README.md").write_text("resolved readme")
    manager.add_file("README.md")
    assert manager.get_repository_state() == "MERGING"

    # Act 3: Continue (which means commit for a merge)
    result = manager.continue_conflict_resolution()

    # Assert 3: Success
    assert "Merge finalized and pushed successfully" in result["message"]
    assert manager.get_repository_state() == "CLEAN"
    new_head = manager.repo.head.peel()
    assert len(new_head.parents) == 2
    assert not (Path(manager.repo.path) / "MERGE_MSG").exists()


def test_list_and_switch_branches(
    git_manager: GitManager, second_clone_repo: pygit2.Repository
):
    """
    Tests listing branches and successfully switching between them.
    """
    repo = git_manager.repo

    # Arrange: Create a new local branch and a new remote branch
    repo.create_branch("local-feature", repo.head.peel())

    # Create and push a new branch from the 'second_clone' to the 'origin'
    second_repo_head = second_clone_repo.head.peel()
    second_clone_repo.create_branch("remote-feature", second_repo_head)
    second_clone_repo.remotes["origin"].push(["refs/heads/remote-feature"])

    # Act 1: List branches (which includes a fetch)
    branches_info = git_manager.list_branches()

    # Assert 1
    all_branches = branches_info["branches"]
    local_branches = {b["name"] for b in all_branches if not b["is_remote"]}
    remote_branches = {b["name"] for b in all_branches if b["is_remote"]}

    assert "main" in local_branches
    assert "local-feature" in local_branches
    assert "main" in remote_branches
    assert "remote-feature" in remote_branches
    assert branches_info["current_branch"] == "main"

    # Act 2: Switch to local branch
    git_manager.switch_branch("local-feature")
    assert git_manager.get_current_branch() == "local-feature"

    # Act 3: Switch to (and track) remote branch
    git_manager.switch_branch("remote-feature")
    assert git_manager.get_current_branch() == "remote-feature"
    upstream = repo.branches["remote-feature"].upstream
    assert upstream is not None
    assert upstream.name == "refs/remotes/origin/remote-feature"


def test_reset_to_remote_discards_local_work(git_manager: GitManager):
    """
    Tests that reset_to_remote correctly discards local-only commits.
    """
    # Arrange: Create two local commits
    remote_head_hash = git_manager.repo.lookup_reference(
        "refs/remotes/origin/main"
    ).target
    make_commit(git_manager.repo, "local1.md", "", "local 1")
    make_commit(git_manager.repo, "local2.md", "", "local 2")
    assert git_manager.repo.head.target != remote_head_hash

    # Act
    result = git_manager.reset_to_remote()

    # Assert
    assert "Reset branch 'main' to remote state" in result["message"]
    assert git_manager.repo.head.target == remote_head_hash
    assert not (Path(git_manager.repo.workdir) / "local1.md").exists()
    assert not (Path(git_manager.repo.workdir) / "local2.md").exists()


def test_checkout_file_from_commit(git_manager: GitManager):
    """
    Tests restoring a file to a previous state from a specific commit.
    """
    repo_path = Path(git_manager.repo.workdir)
    readme_path = repo_path / "README.md"
    original_content = readme_path.read_text()

    # Arrange: Make a new commit that changes README.md
    commit_hash = str(git_manager.repo.head.target)
    readme_path.write_text("New content")
    make_commit(git_manager.repo, "README.md", "New content", "Update README")
    assert "New content" in readme_path.read_text()

    # Act: Checkout the file from the original commit
    git_manager.checkout_file_from_commit(commit_hash, "README.md")

    # Assert
    assert readme_path.read_text() == original_content
