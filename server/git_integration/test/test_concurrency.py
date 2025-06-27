# server/git_integration/test/test_concurrency.py
import asyncio
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Import the router directly, not the app
from ..core.git_service import GitService
from ..git_router import (
    get_git_service,
    get_locked_git_service,
    git_operation_lock,
)
from ..git_router import router as git_router


def create_test_app(git_service: GitService) -> FastAPI:
    """A factory to create a fresh app for each test."""
    test_app = FastAPI()
    test_app.include_router(git_router, prefix="/api/git")

    # Apply the overrides to this specific app instance
    test_app.dependency_overrides[get_git_service] = lambda: git_service

    # The locked override MUST also yield the same service instance
    async def override_get_locked_service():
        async with git_operation_lock:
            yield git_service

    test_app.dependency_overrides[get_locked_git_service] = override_get_locked_service

    return test_app


@pytest.mark.asyncio
async def test_concurrent_sync_requests_are_serialized(git_service: GitService):
    """
    Verifies that the git_operation_lock serializes concurrent write operations.
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
            time.sleep(0.1)
            result = original_sync_method(*args, **kwargs)
            end_time = time.monotonic()
            call_times[-1]["end"] = end_time
            return result

        with patch.object(git_service, "sync_workspace", side_effect=tracking_sync):
            (Path(git_service.executor.repo.workdir) / "concurrent_test.md").write_text(
                "data"
            )
            task1 = async_client.post("/api/git/sync", json={"message": "feat: Sync 1"})
            task2 = async_client.post("/api/git/sync", json={"message": "Sync 2"})
            responses = await asyncio.gather(task1, task2)

            status_codes = sorted([r.status_code for r in responses])
            assert status_codes == [200, 200]
            assert len(call_times) == 2
            call_times.sort(key=lambda x: x["start"])
            first_call, second_call = call_times
            assert second_call["start"] >= first_call["end"]


@pytest.mark.asyncio
async def test_read_operation_is_not_blocked_by_write_operation(
    git_service: GitService,
):
    """
    Verifies that a read operation (/status) can proceed even if a write
    operation (/sync) is holding the lock.
    """
    app = create_test_app(git_service)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_client:
        real_acquire = git_operation_lock.acquire
        real_release = git_operation_lock.release
        lock_acquired_time = 0
        lock_released_time = 0

        async def slow_acquire(*args, **kwargs):
            nonlocal lock_acquired_time
            await real_acquire(*args, **kwargs)
            lock_acquired_time = time.monotonic()
            await asyncio.sleep(0.2)

        def fast_release(*args, **kwargs):
            nonlocal lock_released_time
            lock_released_time = time.monotonic()
            return real_release(*args, **kwargs)

        with patch(
            "git_integration.git_router.git_operation_lock.acquire",
            side_effect=slow_acquire,
        ), patch(
            "git_integration.git_router.git_operation_lock.release",
            side_effect=fast_release,
        ):
            write_task = asyncio.create_task(
                async_client.post("/api/git/sync", json={"message": "Slow write op"})
            )
            await asyncio.sleep(0.05)
            read_response = await async_client.get("/api/git/status")
            read_complete_time = time.monotonic()
            write_response = await write_task

        assert read_response.status_code == 200
        assert write_response.status_code == 200
        lock_held_duration = lock_released_time - lock_acquired_time
        assert read_complete_time < lock_released_time
        assert lock_held_duration >= 0.2
