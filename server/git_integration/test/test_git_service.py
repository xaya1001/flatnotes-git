# server/git_integration/test/test_git_service.py
from pathlib import Path
from unittest.mock import MagicMock, patch

import pygit2
import pytest

from .. import git_config
from ..core.exceptions import GitManagerError, MergeConflictError
from ..core.git_service import GitService
from .conftest import make_commit

# --- Unit Tests with Mocks ---


@pytest.fixture
def mock_repo():
    mock = MagicMock()
    mock.repo.status.return_value = {}
    return mock


@pytest.fixture
def mock_executor():
    mock = MagicMock()
    mock.commit.return_value = {"hash": "0" * 40}
    return mock


@pytest.fixture
def mocked_git_service(mock_repo, mock_executor):
    """A service instance with mocked dependencies for unit testing orchestration."""
    return GitService(repository=mock_repo, executor=mock_executor)


def test_sync_workspace_clean_does_not_commit(
    mocked_git_service, mock_repo, mock_executor
):
    mock_repo.repo.status.return_value = {}
    mock_repo.get_ahead_behind.return_value = (0, 0)
    mocked_git_service.sync_workspace("test message")
    mock_executor.add_all.assert_not_called()
    mock_executor.commit.assert_not_called()


def test_sync_workspace_dirty_commits_and_pulls(
    mocked_git_service, mock_repo, mock_executor
):
    mock_repo.repo.status.return_value = {"file.md": 1}
    mock_repo.get_ahead_behind.return_value = (0, 1)
    with patch.object(mocked_git_service, "pull") as mock_pull:
        mocked_git_service.sync_workspace("test message")
        mock_executor.add_all.assert_called_once()
        mock_executor.commit.assert_called_with(message="test message")
        mock_pull.assert_called_once()


# --- Integration Tests with Real Fixtures ---


def test_pull_with_merge_strategy_creates_merge_commit(
    git_service: GitService, second_clone_repo: pygit2.Repository, monkeypatch
):
    """Verify the pull workflow using the merge strategy."""
    monkeypatch.setattr(git_config, "GIT_PULL_STRATEGY", git_config.PullStrategy.MERGE)
    make_commit(second_clone_repo, "remote_file.md", "", "Remote commit")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])
    make_commit(git_service.repository.repo, "local_file.md", "", "Local commit")
    git_service.pull()
    new_head = git_service.repository.repo.head.peel()
    assert len(new_head.parents) == 2
    assert git_service.get_status()["repository_state"] == "CLEAN"


def test_rebase_conflict_resolution_workflow(
    git_service: GitService, second_clone_repo: pygit2.Repository, monkeypatch
):
    """Verify the complete rebase conflict resolution workflow."""
    monkeypatch.setattr(git_config, "GIT_PULL_STRATEGY", git_config.PullStrategy.REBASE)
    make_commit(
        git_service.repository.repo, "README.md", "Local change to README", "Local"
    )
    make_commit(second_clone_repo, "README.md", "Remote change to README", "Remote")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])
    with pytest.raises(MergeConflictError):
        git_service.pull()
    assert git_service.get_status()["repository_state"] == "REBASING_CONFLICT"
    (Path(git_service.repository.repo.workdir) / "README.md").write_text("Resolved")
    git_service.add_file("README.md")
    assert git_service.get_status()["repository_state"] == "REBASING_CONTINUE"
    result = git_service.resolve_conflict("continue")
    assert "Rebase finished and pushed" in result["message"]
    assert git_service.get_status()["repository_state"] == "CLEAN"


def test_abort_conflict_with_temp_commit_resets_it(
    git_service: GitService, second_clone_repo: pygit2.Repository
):
    """Verify that aborting a conflict triggered by a temp commit correctly rolls back."""
    make_commit(second_clone_repo, "README.md", "Remote change", "Remote commit")
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])
    (Path(git_service.repository.repo.workdir) / "README.md").write_text(
        "My temporary local change"
    )
    original_head_oid = git_service.repository.repo.head.target
    with pytest.raises(MergeConflictError):
        git_service.sync_workspace("temp sync commit")
    assert "CONFLICT" in git_service.get_status()["repository_state"]
    result = git_service.resolve_conflict("abort")
    assert "temp sync commit has been undone" in result["stdout"]
    assert git_service.repository.repo.head.target == original_head_oid
    status = git_service.get_status()
    assert status["files"][0]["path"] == "README.md"
    assert status["files"][0]["index_status"] == "M"


def test_abort_conflict_preserves_user_commit(
    git_service: GitService, second_clone_repo: pygit2.Repository, monkeypatch
):
    """
    Verify that aborting a pull conflict does NOT remove a user's own commit.
    """
    monkeypatch.setattr(git_config, "GIT_PULL_STRATEGY", git_config.PullStrategy.REBASE)
    user_commit_oid = make_commit(
        git_service.repository.repo, "user_file.md", "user content", "feat: my work"
    )
    make_commit(
        second_clone_repo, "user_file.md", "conflicting content", "fix: remote change"
    )
    second_clone_repo.remotes["origin"].push(["refs/heads/main"])
    with pytest.raises(MergeConflictError):
        git_service.pull()
    assert git_service.get_status()["repository_state"] == "REBASING_CONFLICT"
    result = git_service.resolve_conflict("abort")
    assert "Your commit history is untouched" in result["stdout"]
    assert git_service.repository.repo.head.target == user_commit_oid


def test_switch_branch_fails_on_dirty_workspace(git_service: GitService):
    """
    Verify that switching branches is not allowed with uncommitted changes.
    """
    repo = git_service.repository.repo
    repo.create_branch("new-feature", repo.head.peel())
    (Path(repo.workdir) / "README.md").write_text("This is a dirty change.")

    with pytest.raises(
        GitManagerError, match="Cannot switch branch with uncommitted changes"
    ):
        git_service.switch_branch("new-feature")

    assert git_service.get_status()["current_branch"] == "main"


def test_reset_to_remote_discards_all_local_changes(git_service: GitService):
    """
    Verify reset_to_remote discards commits, staged files, and working dir changes.
    """
    repo = git_service.repository.repo
    workdir = Path(repo.workdir)
    remote_head_oid = repo.branches["origin/main"].target
    make_commit(repo, "committed.md", "committed", "feat: local only")
    (workdir / "staged.md").write_text("staged")
    repo.index.add("staged.md")
    repo.index.write()
    (workdir / "README.md").write_text("modified readme")
    git_service.reset_to_remote()
    status = git_service.get_status()
    assert status["files_changed_count"] == 0
    assert not (workdir / "committed.md").exists()
    assert not (workdir / "staged.md").exists()
    assert "Initial commit" in (workdir / "README.md").read_text()
    assert repo.head.target == remote_head_oid
