from pathlib import Path

import pygit2
import pytest
from git_helpers import make_commit
from httpx import ASGITransport, AsyncClient

from git_integration import git_config
from main import app, auth

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


async def test_sync_workflow_happy_path(async_client: AsyncClient, repo_with_remote):
    """
    Tests the full /api/git/sync workflow via HTTP requests.
    This simulates creating a new note and syncing it.
    """
    # 1. ARRANGE: Simulate a new note being created on the filesystem.
    repo_path = Path(repo_with_remote.workdir)
    (repo_path / "new-e2e-note.md").write_text("Hello from API test")

    # 2. ACT: Call the /api/git/sync endpoint, simulating the user clicking "Commit & Sync".
    response = await async_client.post(
        "/api/git/sync", json={"message": "feat: Add new note via API test"}
    )

    # 3. ASSERT: Verify the backend response.
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["message"] == "Workspace synchronized successfully."
    assert "commit" in json_response["details"]
    assert "pull" in json_response["details"]
    assert "push" in json_response["details"]

    # 4. ASSERT: Verify the state of the Git repository (the ground truth).
    status_response = await async_client.get("/api/git/status")
    assert status_response.status_code == 200
    assert status_response.json()["files_changed_count"] == 0

    # Verify that the remote repository received the commit.
    clone_dir = repo_path.parent / "remote_clone_check"
    remote_repo_url = repo_with_remote.remotes["origin"].url
    cloned_repo = pygit2.clone_repository(remote_repo_url, str(clone_dir))

    latest_commit = cloned_repo.head.peel()
    assert "feat: Add new note via API test" in latest_commit.message


async def test_conflict_resolution_workflow(
    async_client: AsyncClient, repo_with_remote, second_clone_repo, monkeypatch
):  # <--- ADD monkeypatch
    """
    Tests the full conflict resolution flow via API calls, specifically for REBASE.
    """
    # Force the pull strategy to 'rebase' for this specific test
    monkeypatch.setattr(git_config, "GIT_PULL_STRATEGY", git_config.PullStrategy.REBASE)

    repo_path = Path(repo_with_remote.workdir)

    # 1. ARRANGE: Create a conflict scenario.
    (repo_path / "conflict.md").write_text("Local version of the file")

    make_commit(
        second_clone_repo, "conflict.md", "Remote version", "fix: conflicting change"
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])

    # 2. ACT & ASSERT: Trigger the conflict by calling /sync.
    sync_response = await async_client.post(
        "/api/git/sync", json={"message": "feat: This will conflict"}
    )
    assert sync_response.status_code == 409
    conflict_data = sync_response.json()["detail"]
    assert "REBASING_CONFLICT" in conflict_data["state"]
    assert "conflict.md" in conflict_data["conflicted_files"]

    # 3. ARRANGE: Simulate the user resolving the conflict.
    (repo_path / "conflict.md").write_text("Resolved content")

    # 4. ACT: Stage the resolved file.
    stage_response = await async_client.post(
        "/api/git/stage_file", json={"filepath": "conflict.md"}
    )
    assert stage_response.status_code == 200

    # Check status: repository should now be in a state ready to continue.
    status_response = await async_client.get("/api/git/status")
    assert status_response.json()["repository_state"] == "REBASING_CONTINUE"

    # 5. ACT: Call the /conflict/continue endpoint.
    continue_response = await async_client.post("/api/git/conflict/continue")

    # 6. ASSERT: The operation should succeed.
    assert continue_response.status_code == 200
    assert "Rebase finished and pushed" in continue_response.json()["message"]

    # Final status check: the repository should be clean.
    final_status = await async_client.get("/api/git/status")
    assert final_status.json()["repository_state"] == "CLEAN"
    assert final_status.json()["files_changed_count"] == 0


@pytest.mark.asyncio
async def test_unauthenticated_access_is_rejected(
    git_service,
):
    """
    Verifies that accessing a protected Git endpoint without authentication
    results in a 401 Unauthorized error.
    This test explicitly does NOT use the dependency_overrides.
    """
    from git_integration.git_router import get_git_service

    # 1. ARRANGE
    app.dependency_overrides[get_git_service] = lambda: git_service

    if not auth:
        pytest.skip("Skipping auth test because authentication is disabled.")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 2. ACTION
        response = await client.get("/api/git/status")

        # 3. ASSERT
        assert response.status_code == 401

    # 4. CLEANUP
    app.dependency_overrides.clear()
