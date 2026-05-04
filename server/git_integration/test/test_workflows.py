# server/git_integration/test/test_workflows.py
from pathlib import Path

import pygit2
import pytest
from httpx import AsyncClient

from .. import git_config
from .conftest import make_commit

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_happy_path_sync_workflow(
    async_client: AsyncClient, repo_with_remote: pygit2.Repository
):
    """
    Tests the full /api/git/sync workflow for a simple, conflict-free change.
    This simulates creating a new note and syncing it.
    """
    # 1. ARRANGE: A user creates a new note. This creates a new file on the server.
    repo_path = Path(repo_with_remote.workdir)
    (repo_path / "new-workflow-note.md").write_text("Hello from workflow test")

    # 2. ACTION: The user clicks "Commit & Sync". The frontend calls the /sync endpoint.
    response = await async_client.post(
        "/api/git/sync", json={"message": "feat: Add new note via workflow test"}
    )

    # 3. ASSERT: The API call is successful.
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["message"] == "Workspace synchronized successfully."
    assert "commit" in json_response["details"]
    assert "push" in json_response["details"]

    # 4. ASSERT: The repository state is now clean.
    status_response = await async_client.get("/api/git/status")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["files_changed_count"] == 0
    assert status_data["repository_state"] == "CLEAN"
    assert status_data["commits_ahead"] == 0
    assert status_data["commits_behind"] == 0

    # 5. ASSERT: The remote repository received the commit.
    remote_repo_url = repo_with_remote.remotes["origin"].url
    clone_dir = repo_path.parent / "remote_clone_check"
    cloned_repo = pygit2.clone_repository(remote_repo_url, str(clone_dir))
    latest_commit = cloned_repo.head.peel()
    assert "feat: Add new note via workflow test" in latest_commit.message


async def test_rebase_conflict_resolution_workflow(
    async_client: AsyncClient,
    repo_with_remote: pygit2.Repository,
    second_clone_repo: pygit2.Repository,
    monkeypatch,
):
    """
    Tests the full conflict resolution flow: sync -> conflict -> resolve -> continue -> success.
    """
    # ARRANGE: Force the pull strategy to 'rebase' for this test's determinism.
    monkeypatch.setattr(git_config, "GIT_PULL_STRATEGY", git_config.PullStrategy.REBASE)
    repo_path = Path(repo_with_remote.workdir)

    # 1. ARRANGE: Create a conflict scenario.
    # User A (main repo) modifies a file locally.
    (repo_path / "conflict.md").write_text("Local version of the file")

    # User B (second clone) pushes a conflicting change to the same file.
    make_commit(
        second_clone_repo, "conflict.md", "Remote version", "fix: conflicting change"
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. ACTION & ASSERT: User A syncs, triggering the conflict.
    sync_response = await async_client.post(
        "/api/git/sync", json={"message": "feat: This will conflict"}
    )
    assert sync_response.status_code == 409
    conflict_data = sync_response.json()["detail"]
    assert conflict_data["state"] == "REBASING_CONFLICT"
    assert "conflict.md" in conflict_data["conflicted_files"]

    # 3. ARRANGE: User A resolves the conflict on the filesystem.
    (repo_path / "conflict.md").write_text("Resolved content")

    # 4. ACTION: User A stages the resolved file via the UI.
    stage_response = await async_client.post(
        "/api/git/stage_file", json={"filepath": "conflict.md"}
    )
    assert stage_response.status_code == 200

    # 5. ASSERT: The repository state is now ready to continue the rebase.
    status_response = await async_client.get("/api/git/status")
    assert status_response.json()["repository_state"] == "REBASING_CONTINUE"

    # 6. ACTION: User A clicks "Continue" in the UI.
    continue_response = await async_client.post("/api/git/conflict/continue")

    # 7. ASSERT: The operation succeeds, and the repo is clean.
    assert continue_response.status_code == 200
    assert "Rebase finished and pushed" in continue_response.json()["message"]

    final_status = await async_client.get("/api/git/status")
    final_status_data = final_status.json()
    assert final_status_data["repository_state"] == "CLEAN"
    assert final_status_data["files_changed_count"] == 0


async def test_sync_conflict_and_abort_workflow(
    async_client: AsyncClient,
    repo_with_remote: pygit2.Repository,
    second_clone_repo: pygit2.Repository,
):
    """
    Tests the flow where a sync causes a conflict, and the user chooses to abort.
    The repository should be returned to the state *before* the sync was initiated.
    """
    repo_path = Path(repo_with_remote.workdir)

    # 1. ARRANGE: Create conflict scenario.
    (repo_path / "abort-test.md").write_text("Initial local content")
    make_commit(
        second_clone_repo, "abort-test.md", "Remote content", "fix: remote change"
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. ACTION: Trigger the conflict.
    sync_response = await async_client.post(
        "/api/git/sync", json={"message": "feat: sync to be aborted"}
    )
    assert sync_response.status_code == 409

    # 3. ACTION: User clicks "Abort".
    abort_response = await async_client.post("/api/git/conflict/abort")
    assert abort_response.status_code == 200
    assert "temp sync commit has been undone" in abort_response.json()["stdout"]

    # 4. ASSERT: The repository state is restored.
    # The initial change should be back in the index (staged), as if the user
    # had just clicked "Stage All" but not yet committed.
    status_response = await async_client.get("/api/git/status")
    status_data = status_response.json()
    assert status_data["repository_state"] == "CLEAN"
    assert len(status_data["files"]) == 1
    file_status = status_data["files"][0]
    assert file_status["path"] == "abort-test.md"
    assert file_status["index_status"] == "A"  # Added to the index
    assert file_status["work_tree_status"] == " "  # But clean in the working dir


async def test_push_rejected_workflow(
    async_client: AsyncClient,
    repo_with_remote: pygit2.Repository,
    second_clone_repo: pygit2.Repository,
):
    """
    Tests the scenario where a push fails due to non-fast-forward,
    which should prompt the user to pull first.
    """
    # 1. ARRANGE: User A makes a commit but does not push.
    # First, modify the file on disk.
    (Path(repo_with_remote.workdir) / "README.md").write_text("User A's change")
    # Then, stage the modified file.
    await async_client.post("/api/git/stage_file", json={"filepath": "README.md"})
    # Now, the commit will have changes.
    commit_response = await async_client.post(
        "/api/git/commit", json={"message": "User A commit"}
    )
    assert commit_response.status_code == 200  # Ensure the commit succeeded

    # 2. ARRANGE: User B pushes an unrelated change, making the remote ahead.
    make_commit(second_clone_repo, "user-b-file.md", "", "User B commit")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 3. ACTION: User A tries to push.
    push_response = await async_client.post("/api/git/push")

    # 4. ASSERT: The API correctly returns a 409 with a specific 'PUSH_REJECTED' state.
    assert push_response.status_code == 409
    error_data = push_response.json()["detail"]
    assert error_data["state"] == "PUSH_REJECTED_NON_FAST_FORWARD"
    assert "Please pull the latest changes" in error_data["message"]


async def test_restore_deleted_file_workflow(
    async_client: AsyncClient, repo_with_remote: pygit2.Repository
):
    """
    Tests the ability to restore a file that was deleted in a previous commit.
    """
    repo_path = Path(repo_with_remote.workdir)
    file_to_delete = "file-to-be-deleted.md"

    # 1. ARRANGE: Create and commit a new file.
    make_commit(
        repo_with_remote, file_to_delete, "This file will be deleted.", "feat: add file"
    )
    assert (repo_path / file_to_delete).exists()

    # 2. ARRANGE: Delete the file and commit the deletion.
    (repo_path / file_to_delete).unlink()
    repo_with_remote.index.remove(file_to_delete)
    repo_with_remote.index.write()
    # Manually create the commit from the prepared index state.
    tree = repo_with_remote.index.write_tree()
    author = pygit2.Signature("Helper", "helper@test.com")
    parents = [repo_with_remote.head.target]
    delete_commit_hash = str(
        repo_with_remote.create_commit(
            "HEAD",
            author,
            author,
            "fix: remove unnecessary file",
            tree,
            parents,
        )
    )
    assert not (repo_path / file_to_delete).exists()

    # 3. ACTION: User finds the deletion commit in the history and clicks "Restore".
    restore_response = await async_client.post(
        "/api/git/restore-file",
        json={"commit_hash": delete_commit_hash, "filepath": file_to_delete},
    )

    # 4. ASSERT: The API call is successful.
    assert restore_response.status_code == 200
    assert (
        f"File '{file_to_delete}' restored from commit"
        in restore_response.json()["message"]
    )

    # 5. ASSERT: The file now exists in the working directory with its old content.
    assert (repo_path / file_to_delete).exists()
    assert (repo_path / file_to_delete).read_text() == "This file will be deleted."

    # 6. ASSERT: The repository status shows the restored file as a change.
    status_response = await async_client.get("/api/git/status")
    status_data = status_response.json()
    assert status_data["files_changed_count"] > 0
    restored_file_status = next(
        f for f in status_data["files"] if f["path"] == file_to_delete
    )
    assert restored_file_status is not None


async def test_pull_fails_on_dirty_workspace(
    async_client: AsyncClient, repo_with_remote: pygit2.Repository
):
    """
    Tests that a standalone pull is rejected if the workspace has uncommitted changes.
    """
    # 1. ARRANGE: Make the workspace dirty.
    (Path(repo_with_remote.workdir) / "README.md").write_text("Uncommitted change")

    # 2. ACTION: Attempt to pull.
    pull_response = await async_client.post("/api/git/pull")

    # 3. ASSERT: The API rejects the request with a 400 error.
    assert pull_response.status_code == 400
    assert "Cannot pull with uncommitted changes" in pull_response.json()["detail"]


async def test_branch_switching_workflow(
    async_client: AsyncClient, repo_with_remote: pygit2.Repository
):
    """
    Tests the success and failure scenarios for switching branches.
    """
    # 1. ARRANGE: Create a new branch.
    repo = repo_with_remote
    feature_branch_name = "feat/new-thing"
    repo.create_branch(feature_branch_name, repo.head.peel())

    # 2. ACTION & ASSERT (Success): Switch to the new branch with a clean workspace.
    switch_success_response = await async_client.post(
        "/api/git/branches/switch", json={"branch_name": feature_branch_name}
    )
    assert switch_success_response.status_code == 200
    status_response = await async_client.get("/api/git/status")
    assert status_response.json()["current_branch"] == feature_branch_name

    # 3. ARRANGE: Make the workspace dirty while on the feature branch.
    (Path(repo.workdir) / "feature-file.md").write_text("Work in progress")

    # 4. ACTION & ASSERT (Failure): Attempt to switch back to main.
    switch_fail_response = await async_client.post(
        "/api/git/branches/switch", json={"branch_name": "main"}
    )
    assert switch_fail_response.status_code == 400
    assert (
        "Cannot switch branch with uncommitted changes"
        in switch_fail_response.json()["detail"]
    )

    # 5. ASSERT: The branch remains unchanged.
    status_response = await async_client.get("/api/git/status")
    assert status_response.json()["current_branch"] == feature_branch_name


async def test_reset_to_remote_workflow(
    async_client: AsyncClient, repo_with_remote: pygit2.Repository
):
    """
    Tests that the reset-to-remote endpoint correctly discards all local
    commits, staged changes, and unstaged changes.
    """
    repo_path = Path(repo_with_remote.workdir)
    remote_head_hash = repo_with_remote.branches["origin/main"].target

    # 1. ARRANGE: Create a complex local state that differs from the remote.
    # - A new commit that is not on the remote.
    make_commit(
        repo_with_remote,
        "local-only.md",
        "This commit should be deleted.",
        "feat: new local feature",
    )
    # - A staged change.
    (repo_path / "staged-change.md").write_text("This should be discarded.")
    repo_with_remote.index.add("staged-change.md")
    repo_with_remote.index.write()
    # - An unstaged change.
    (repo_path / "README.md").write_text("Modified README, should be reverted.")

    # 2. ACTION: The user clicks the "Reset to Remote" button.
    response = await async_client.post(
        "/api/git/reset-to-remote", json={"confirm": True}
    )

    # 3. ASSERT: The API call is successful.
    assert response.status_code == 200
    assert "Reset branch 'main' to remote state" in response.json()["message"]

    # 4. ASSERT: The repository is now perfectly clean and matches the remote.
    final_status = await async_client.get("/api/git/status")
    final_status_data = final_status.json()
    assert final_status_data["files_changed_count"] == 0
    assert final_status_data["repository_state"] == "CLEAN"
    assert final_status_data["commits_ahead"] == 0
    assert final_status_data["commits_behind"] == 0

    # Verify HEAD points to the original remote commit
    new_head_hash = repo_with_remote.head.target
    assert new_head_hash == remote_head_hash


async def test_reset_to_remote_requires_confirmation(async_client: AsyncClient):
    response = await async_client.post(
        "/api/git/reset-to-remote", json={"confirm": False}
    )

    assert response.status_code == 400
    assert "requires confirm=true" in response.json()["detail"]


async def test_git_file_operation_rejects_path_traversal(async_client: AsyncClient):
    response = await async_client.post(
        "/api/git/stage_file", json={"filepath": "../outside.md"}
    )

    assert response.status_code == 422


async def test_git_file_operation_rejects_backslash_paths(async_client: AsyncClient):
    response = await async_client.post(
        "/api/git/stage_file", json={"filepath": "..\\outside.md"}
    )

    assert response.status_code == 422


async def test_switch_branch_rejects_invalid_branch_name(async_client: AsyncClient):
    response = await async_client.post(
        "/api/git/branches/switch", json={"branch_name": "bad branch"}
    )

    assert response.status_code == 422


async def test_switch_branch_rejects_invalid_branch_component(
    async_client: AsyncClient,
):
    response = await async_client.post(
        "/api/git/branches/switch", json={"branch_name": "feature/.hidden"}
    )

    assert response.status_code == 422


async def test_restore_file_rejects_invalid_commit_hash(async_client: AsyncClient):
    response = await async_client.post(
        "/api/git/restore-file",
        json={"commit_hash": "not-a-hash", "filepath": "README.md"},
    )

    assert response.status_code == 422
