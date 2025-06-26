# server/git_integration/test/conftest.py
from pathlib import Path
from typing import Iterator

import pygit2
import pytest

from ..git_config import PullStrategy
from ..git_manager import GitManager


# --- Fixture Scopes ---
# 'function': The fixture is created for each test function. This ensures test isolation.
def make_commit(
    repo: pygit2.Repository, filename: str, content: str, message: str
) -> pygit2.Oid:
    """Helper function to make a commit in a non-bare repository."""
    (Path(repo.workdir) / filename).write_text(content)
    index = repo.index
    index.add(filename)
    index.write()
    tree_id = index.write_tree()

    author = pygit2.Signature("Helper", "helper@test.com")
    parents = [] if repo.head_is_unborn else [repo.head.target]

    return repo.create_commit("HEAD", author, author, message, tree_id, parents)


# 'session': The fixture is created once for the entire test session.

# --- Core Repository Fixtures ---


@pytest.fixture(scope="function")
def temp_repo_path(tmp_path: Path) -> Iterator[Path]:
    """
    Creates a temporary directory for a new git repository.
    Yields the path to this directory and cleans it up afterward.
    """
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    yield repo_dir
    # Cleanup is handled by pytest's tmp_path fixture


@pytest.fixture(scope="function")
def bare_repo_path(tmp_path: Path) -> Iterator[Path]:
    """
    Creates a temporary bare git repository to act as a remote 'origin'.
    """
    remote_dir = tmp_path / "test_repo.git"
    pygit2.init_repository(str(remote_dir), bare=True)
    yield remote_dir


@pytest.fixture(scope="function")
def repo_with_initial_commit(temp_repo_path: Path) -> pygit2.Repository:
    """
    Creates a standard git repository and adds an initial commit that includes
    a .gitignore file, ensuring the repo is clean after GitManager init.
    """
    repo = pygit2.init_repository(str(temp_repo_path), initial_head="main")

    # Create initial files, including .gitignore
    (temp_repo_path / "README.md").write_text("Initial commit.")
    (temp_repo_path / ".gitignore").write_text(".flatnotes/\n")

    index = repo.index
    index.add("README.md")
    index.add(".gitignore")
    index.write()

    author = pygit2.Signature("Test Author", "test@example.com")
    committer = pygit2.Signature("Test Committer", "test@example.com")
    tree = index.write_tree()

    repo.create_commit(
        "HEAD",
        author,
        committer,
        "Initial commit",
        tree,
        [],
    )
    return repo


@pytest.fixture(scope="function")
def repo_with_remote(
    repo_with_initial_commit: pygit2.Repository, bare_repo_path: Path
) -> pygit2.Repository:
    """
    Connects the local repository to the bare remote repository and pushes the initial state.
    This fixture is essential for integration tests (pull/push).
    """
    repo = repo_with_initial_commit
    repo.remotes.create("origin", str(bare_repo_path))

    main_ref = "refs/heads/main"
    repo.remotes["origin"].push([f"{main_ref}:{main_ref}"])

    # Correctly set the HEAD of the bare repository using the 'create' method.
    bare_repo = pygit2.Repository(bare_repo_path)
    bare_repo.references.create("HEAD", main_ref, force=True)

    # Set up upstream tracking information for the local branch
    main_branch = repo.branches["main"]
    main_branch.upstream = repo.branches["origin/main"]

    return repo


@pytest.fixture
def second_clone_repo(
    repo_with_remote: pygit2.Repository, tmp_path: Path
) -> pygit2.Repository:
    """
    Creates a second, separate clone of the bare remote repository.
    This fixture is used to simulate actions from another user.
    The `repo_with_remote` fixture ensures the bare repo is populated first.
    """
    clone_path = tmp_path / "second_clone"
    bare_repo_url = repo_with_remote.remotes["origin"].url

    repo = pygit2.clone_repository(bare_repo_url, str(clone_path))

    # Configure user for this repo to avoid issues
    config = repo.config
    config.set_multivar("user.name", ".*", "Second User")
    config.set_multivar("user.email", ".*", "second@user.com")

    return repo


# --- GitManager Instance Fixtures ---


@pytest.fixture
def git_manager(repo_with_remote: pygit2.Repository) -> GitManager:
    """
    Provides a GitManager instance configured to use the test repository
    with a remote. This is the primary fixture for most integration tests.
    """
    return GitManager(
        repo_path=repo_with_remote.workdir,
        default_branch="main",
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name="Test User",
        user_email="user@test.com",
    )


@pytest.fixture
def git_manager_merge_strategy(repo_with_remote: pygit2.Repository) -> GitManager:
    """
    Provides a GitManager instance configured with the MERGE pull strategy.
    """
    return GitManager(
        repo_path=repo_with_remote.workdir,
        default_branch="main",
        default_remote="origin",
        pull_strategy=PullStrategy.MERGE,
        user_name="Test User",
        user_email="user@test.com",
    )


@pytest.fixture
def unborn_repo_path(temp_repo_path: Path) -> Path:
    """
    Initializes a repository but does not create any commits, leaving it
    in an 'unborn' state.
    """
    pygit2.init_repository(str(temp_repo_path), initial_head="main")
    return temp_repo_path


@pytest.fixture
def git_manager_unborn(unborn_repo_path: Path) -> GitManager:
    """
    Provides a GitManager instance for a repository with no commits.
    """
    return GitManager(
        repo_path=str(unborn_repo_path),
        default_branch="main",
        default_remote="origin",
        pull_strategy=PullStrategy.REBASE,
        user_name="Test User",
        user_email="user@test.com",
    )
