# server/git_integration/test/conftest.py
from pathlib import Path
from typing import AsyncGenerator, Iterator

import pygit2
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app

# import paths
from ..core.git_executor import Executor
from ..core.git_repository import Repository
from ..core.git_service import GitService


# Helper function
def make_commit(
    repo: pygit2.Repository, filename: str, content: str, message: str
) -> pygit2.Oid:
    (Path(repo.workdir) / filename).write_text(content)
    index = repo.index
    index.add(filename)
    index.write()
    tree_id = index.write_tree()
    author = pygit2.Signature("Helper", "helper@test.com")
    parents = [] if repo.head_is_unborn else [repo.head.target]
    return repo.create_commit("HEAD", author, author, message, tree_id, parents)


# Core repository fixtures
@pytest.fixture(scope="function")
def temp_repo_path(tmp_path: Path) -> Iterator[Path]:
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    yield repo_dir


@pytest.fixture(scope="function")
def bare_repo_path(tmp_path: Path) -> Iterator[Path]:
    remote_dir = tmp_path / "test_repo.git"
    pygit2.init_repository(str(remote_dir), bare=True)
    yield remote_dir


@pytest.fixture(scope="function")
def repo_with_initial_commit(temp_repo_path: Path) -> pygit2.Repository:
    repo = pygit2.init_repository(str(temp_repo_path), initial_head="main")
    (temp_repo_path / "README.md").write_text("Initial commit.")
    (temp_repo_path / ".gitignore").write_text(".flatnotes/\n")
    index = repo.index
    index.add("README.md")
    index.add(".gitignore")
    index.write()
    author = pygit2.Signature("Test Author", "test@example.com")
    tree = index.write_tree()
    repo.create_commit("HEAD", author, author, "Initial commit", tree, [])
    return repo


@pytest.fixture(scope="function")
def repo_with_remote(
    repo_with_initial_commit: pygit2.Repository, bare_repo_path: Path
) -> pygit2.Repository:
    repo = repo_with_initial_commit
    repo.remotes.create("origin", str(bare_repo_path))
    main_ref = "refs/heads/main"
    repo.remotes["origin"].push([f"{main_ref}:{main_ref}"])
    bare_repo = pygit2.Repository(bare_repo_path)
    bare_repo.references.create("HEAD", main_ref, force=True)
    main_branch = repo.branches["main"]
    main_branch.upstream = repo.branches["origin/main"]
    return repo


@pytest.fixture
def second_clone_repo(
    repo_with_remote: pygit2.Repository, tmp_path: Path
) -> pygit2.Repository:
    clone_path = tmp_path / "second_clone"
    repo = pygit2.clone_repository(
        repo_with_remote.remotes["origin"].url, str(clone_path)
    )
    config = repo.config
    config.set_multivar("user.name", ".*", "Second User")
    config.set_multivar("user.email", ".*", "second@user.com")
    return repo


# Core Component Fixtures
@pytest.fixture
def repository(repo_with_remote: pygit2.Repository) -> Repository:
    return Repository(
        repo_path=repo_with_remote.workdir,
        default_branch="main",
        default_remote="origin",
    )


@pytest.fixture
def executor(repo_with_remote: pygit2.Repository) -> Executor:
    return Executor(
        repo_path=repo_with_remote.workdir,
        default_branch="main",
        default_remote="origin",
        user_name="Test User",
        user_email="user@test.com",
    )


@pytest.fixture
def git_service(repository: Repository, executor: Executor) -> GitService:
    """Provides a GitService instance with concrete dependencies."""
    return GitService(repository=repository, executor=executor)


# HTTP Client Fixture
@pytest_asyncio.fixture
async def async_client(
    git_service: GitService,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an async client for API testing, injecting the real GitService.
    """
    from ..git_router import get_git_service

    # The function to override the dependency.
    def override_get_service():
        return git_service

    # Apply the override to the FastAPI app instance.
    app.dependency_overrides[get_git_service] = override_get_service

    # Create the test client.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
