import asyncio
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from git_integration.core.git_service import GitService
from git_integration.git_lock import git_operation_lock
from git_integration.git_router import get_git_service
from git_integration.git_router import router as git_router


def create_test_app(git_service: GitService) -> FastAPI:
    """A factory to create a fresh app for each test."""
    test_app = FastAPI()
    test_app.include_router(git_router, prefix="/api/git")

    # Apply the overrides to this specific app instance
    # We ONLY need to override the base service dependency now.
    test_app.dependency_overrides[get_git_service] = lambda: git_service

    return test_app


@pytest.mark.asyncio
async def test_concurrent_sync_requests_are_serialized(git_service: GitService):
    """
    Verifies that the git_operation_lock serializes concurrent write operations.
    This test logic remains valid as the lock is still used inside the route.
    """
    app = create_test_app(git_service)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        call_times = []
        original_sync_method = git_service.sync_workspace

        def tracking_sync(*args, **kwargs):
            start_time = time.monotonic()
            call_times.append({"start": start_time, "end": 0})
            time.sleep(0.1)  # Simulate work
            result = original_sync_method(*args, **kwargs)
            end_time = time.monotonic()
            call_times[-1]["end"] = end_time
            return result

        with patch.object(git_service, "sync_workspace", side_effect=tracking_sync):
            (Path(git_service.executor.repo.workdir) / "concurrent_test.md").write_text(
                "data"
            )
            git_service.executor.repo.index.add("concurrent_test.md")
            git_service.executor.repo.index.write()

            task1 = async_client.post("/api/git/sync", json={"message": "feat: Sync 1"})
            task2 = async_client.post("/api/git/sync", json={"message": "Sync 2"})
            responses = await asyncio.gather(task1, task2)

            status_codes = sorted([r.status_code for r in responses])
            assert status_codes == [200, 200]
            assert len(call_times) == 2
            call_times.sort(key=lambda x: x["start"])
            first_call, second_call = call_times
            # The key assertion: the second call must start after the first one ends.
            assert second_call["start"] >= first_call["end"]


@pytest.mark.asyncio
async def test_read_operation_is_not_blocked_by_write_operation(
    git_service: GitService,
):
    """
    Verifies that a read operation (/status) can proceed even if a write
    operation (/sync) is waiting on the lock. This remains valid because
    the /status route does not use the lock.
    """
    app = create_test_app(git_service)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        (Path(git_service.executor.repo.workdir) / "write_op.md").write_text("data")

        git_operation_lock.acquire()
        try:
            write_task = asyncio.create_task(
                async_client.post("/api/git/sync", json={"message": "Slow write op"})
            )
            await asyncio.sleep(0.05)

            read_response = await async_client.get("/api/git/status")
            assert read_response.status_code == 200
            assert not write_task.done()
        finally:
            git_operation_lock.release()

        write_response = await write_task

        assert write_response.status_code == 200
