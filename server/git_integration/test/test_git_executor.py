# server/git_integration/test/test_git_executor.py
from pathlib import Path

import pygit2
import pytest
from pygit2.enums import FileStatus

from .. import git_config
from ..core.git_exceptions import NoChangesError, PushRejectedError
from ..core.git_executor import Executor
from .conftest import make_commit


def test_init_auto_init_creates_repo(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(git_config, "GIT_AUTO_INIT", True)
    executor = Executor(
        repo_path=str(tmp_path),
        default_branch="main",
        default_remote="origin",
        user_name="Test",
        user_email="test@email.com",
    )
    assert (tmp_path / ".git").is_dir()
    assert executor.repo.head_is_unborn


def test_add_all_stages_all_changes(executor: Executor):
    """Verify that add_all stages all types of changes."""
    repo_path = Path(executor.repo.workdir)
    # Arrange
    (repo_path / "new_file.txt").write_text("new")
    (repo_path / "README.md").write_text("modified")
    make_commit(executor.repo, "to_delete.txt", "delete me", "add file to delete")
    (repo_path / "to_delete.txt").unlink()

    # Act
    executor.add_all()

    # Assert
    status = executor.repo.status()
    assert status["new_file.txt"] == FileStatus.INDEX_NEW
    assert status["README.md"] == FileStatus.INDEX_MODIFIED
    assert status["to_delete.txt"] == FileStatus.INDEX_DELETED


def test_add_and_commit(executor: Executor):
    (Path(executor.repo.workdir) / "feature.md").write_text("A new feature.")
    executor.add_file("feature.md")
    commit_info = executor.commit("Add feature.md")
    assert "hash" in commit_info
    head_commit = executor.repo.head.peel()
    assert str(head_commit.id) == commit_info["hash"]
    assert "feature.md" in head_commit.tree
    assert not executor.repo.status()


def test_commit_no_changes_raises_error(executor: Executor):
    with pytest.raises(NoChangesError):
        executor.commit("This should fail")


def test_unstage_file(executor: Executor):
    (Path(executor.repo.workdir) / "temp.md").write_text("temporary content")
    executor.add_file("temp.md")
    assert executor.repo.status()["temp.md"] == FileStatus.INDEX_NEW
    executor.unstage_file("temp.md")
    assert executor.repo.status()["temp.md"] == FileStatus.WT_NEW


def test_discard_file(executor: Executor):
    readme_path = Path(executor.repo.workdir) / "README.md"
    original_content = readme_path.read_text()
    readme_path.write_text("This change should be discarded.")
    executor.discard_file("README.md")
    assert not executor.repo.status()
    assert readme_path.read_text() == original_content


def test_discard_all_cleans_the_entire_workspace(executor: Executor):
    repo_path = Path(executor.repo.workdir)
    (repo_path / "untracked_file.txt").write_text("untracked")
    (repo_path / "untracked_dir").mkdir()
    (repo_path / "untracked_dir" / "nested.txt").write_text("nested")
    (repo_path / "README.md").write_text("This is a modification.")
    executor.discard_all()
    assert not (repo_path / "untracked_file.txt").exists()
    assert not (repo_path / "untracked_dir").exists()
    assert "Initial commit" in (repo_path / "README.md").read_text()


def test_push_to_diverged_remote_raises_push_rejected_error(
    executor: Executor, second_clone_repo: pygit2.Repository
):
    make_commit(second_clone_repo, "remote_only.md", "divergent", "A remote commit")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])
    make_commit(executor.repo, "local_only.md", "local", "A local commit")
    with pytest.raises(PushRejectedError):
        executor.push()


def test_fetch_updates_remote_tracking_branch(
    executor: Executor, second_clone_repo: pygit2.Repository
):
    remote_commit_oid = make_commit(
        second_clone_repo, "remote.md", "data", "remote change"
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])
    local_remote_ref_before = executor.repo.branches["origin/main"]
    assert local_remote_ref_before.target != remote_commit_oid
    executor.fetch()
    local_remote_ref_after = executor.repo.branches["origin/main"]
    assert local_remote_ref_after.target == remote_commit_oid
