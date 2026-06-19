from pathlib import Path

import pygit2
import pytest
from git_helpers import make_commit
from pygit2.enums import SortMode

from git_integration.core.git_exceptions import RepositoryInvalidError
from git_integration.core.git_repository import Repository


def test_init_repository_success(repo_with_initial_commit):
    """Tests that Repository initializes correctly with an existing repo."""
    repo = Repository(
        repo_path=repo_with_initial_commit.workdir,
        default_branch="main",
        default_remote="origin",
    )
    assert repo.repo is not None
    assert repo.repo.workdir == repo_with_initial_commit.workdir


def test_init_no_repository_raises_error(tmp_path: Path):
    """Tests that Repository raises RepositoryInvalidError if no repo exists."""
    with pytest.raises(RepositoryInvalidError):
        Repository(
            repo_path=str(tmp_path),
            default_branch="main",
            default_remote="origin",
        )


def test_get_status_clean(repository: Repository):
    """Tests get_status on a clean repository."""
    status = repository.get_status()
    assert status["files_changed_count"] == 0
    assert status["repository_state"] == "CLEAN"


def test_get_status_dirty(repository: Repository):
    """Tests get_status on a repository with various changes."""
    repo_path = Path(repository.repo.workdir)
    (repo_path / "new_file.md").write_text("new")
    (repo_path / "README.md").write_text("modified")

    repository.repo.index.add("new_file.md")
    repository.repo.index.write()

    status = repository.get_status()
    assert status["files_changed_count"] == 2

    files = {f["path"]: f for f in status["files"]}
    assert files["new_file.md"]["index_status"] == "A"
    assert files["new_file.md"]["work_tree_status"] == " "
    assert files["README.md"]["index_status"] == " "
    assert files["README.md"]["work_tree_status"] == "M"


def test_get_files_in_commit(repository: Repository):
    """Tests getting file changes for a commit with add, modify, and delete."""
    repo_path = Path(repository.repo.workdir)
    (repo_path / "file_to_modify.txt").write_text("original")
    make_commit(
        repository.repo,
        "file_to_modify.txt",
        "original",
        "base: add file to modify",
    )

    (repo_path / "file_to_delete.txt").write_text("delete me")
    commit_oid = make_commit(
        repository.repo,
        "file_to_delete.txt",
        "delete me",
        "base: add file to delete",
    )
    repository.repo.index.read()

    # Now, make the changes we want to inspect
    (repo_path / "file_to_add.txt").write_text("new file")
    (repo_path / "file_to_modify.txt").write_text("modified content")
    (repo_path / "file_to_delete.txt").unlink()
    repository.repo.index.add_all()
    tree_id = repository.repo.index.write_tree()
    commit_hash = str(
        repository.repo.create_commit(
            "HEAD",
            repository.repo.default_signature,
            repository.repo.default_signature,
            "feat: complex changes",
            tree_id,
            [commit_oid],
        )
    )

    files = repository.get_files_in_commit(commit_hash)
    statuses = {f["path"]: f["status"] for f in files}
    assert statuses.get("file_to_add.txt") == "A"
    assert statuses.get("file_to_modify.txt") == "M"
    assert statuses.get("file_to_delete.txt") == "D"


def test_get_files_in_initial_commit(repository: Repository):
    """Tests getting files for the very first commit."""
    walker = repository.repo.walk(
        repository.repo.head.target, SortMode.TOPOLOGICAL | SortMode.REVERSE
    )
    initial_commit_hash = str(next(walker).id)

    files = repository.get_files_in_commit(initial_commit_hash)

    assert len(files) == 2
    assert all(f["status"] == "A" for f in files)
    assert {"README.md", ".gitignore"} == {f["path"] for f in files}


def test_get_files_with_invalid_hash_raises_error(repository: Repository):
    """Tests that get_files_in_commit raises an error for a non-existent hash."""
    with pytest.raises(pygit2.GitError):
        repository.get_files_in_commit("abcdef1234567890abcdef1234567890abcdef12")
