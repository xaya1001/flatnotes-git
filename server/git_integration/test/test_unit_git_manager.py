# server/git_integration/test/test_unit_git_manager.py

from pathlib import Path

import pygit2
import pytest
from pygit2.enums import FileStatus, SortMode

from git_integration.test.conftest import make_commit

from .. import git_config
from ..git_manager import GitManager, NoChangesError, RepositoryInvalidError


def test_init_repository_success(repo_with_initial_commit):
    """
    Tests that GitManager initializes correctly with an existing repository.
    """
    manager = GitManager(
        repo_path=repo_with_initial_commit.workdir,
        default_branch="main",
        default_remote="origin",
        pull_strategy="rebase",
    )
    assert manager.repo is not None
    assert manager.repo.workdir == repo_with_initial_commit.workdir


def test_init_no_repository_raises_error(tmp_path: Path, monkeypatch):
    """
    Tests that GitManager raises RepositoryInvalidError if no repo exists
    and auto-init is disabled.
    """
    # Patch the attribute on the imported module object directly
    monkeypatch.setattr(git_config, "GIT_AUTO_INIT", False)
    with pytest.raises(RepositoryInvalidError):
        GitManager(
            repo_path=str(tmp_path),
            default_branch="main",
            default_remote="origin",
            pull_strategy="rebase",
        )


def test_init_auto_init_creates_repo(tmp_path: Path, monkeypatch):
    """
    Tests that GitManager automatically initializes a new repository
    when the feature flag is enabled.
    """
    # Patch the attribute on the imported module object directly
    monkeypatch.setattr(git_config, "GIT_AUTO_INIT", True)
    manager = GitManager(
        repo_path=str(tmp_path),
        default_branch="main",
        default_remote="origin",
        pull_strategy="rebase",
        user_name="Test",
        user_email="test@email.com",
    )
    assert (tmp_path / ".git").is_dir()
    assert manager.get_current_branch() == "main"
    assert manager.repo.head_is_unborn


def test_enforce_gitignore_creates_file(unborn_repo_path: Path):
    """
    Tests that _enforce_gitignore_rule creates a .gitignore file if it doesn't exist.
    """
    GitManager(
        repo_path=str(unborn_repo_path),
        default_branch="main",
        default_remote="origin",
        pull_strategy="rebase",
    )
    gitignore_path = unborn_repo_path / ".gitignore"
    assert gitignore_path.exists()
    assert ".flatnotes/" in gitignore_path.read_text()


def test_enforce_gitignore_appends_to_existing(repo_with_initial_commit):
    """
    Tests that _enforce_gitignore_rule appends to an existing .gitignore file.
    """
    gitignore_path = Path(repo_with_initial_commit.workdir) / ".gitignore"
    # Overwrite the one from the fixture to test appending
    gitignore_path.write_text("node_modules/\n")

    GitManager(
        repo_path=repo_with_initial_commit.workdir,
        default_branch="main",
        default_remote="origin",
        pull_strategy="rebase",
    )

    content = gitignore_path.read_text()
    assert "node_modules/" in content
    assert ".flatnotes/" in content


def test_get_status_clean(git_manager: GitManager):
    """
    Tests get_status on a clean repository.
    The fixture now provides a repo where .gitignore is already committed.
    """
    status = git_manager.get_status()
    assert status["files_changed_count"] == 0
    assert status["repository_state"] == "CLEAN"


def test_get_status_dirty(git_manager: GitManager):
    """
    Tests get_status on a repository with various changes.
    """
    repo_path = Path(git_manager.repo.workdir)
    (repo_path / "new_file.md").write_text("new")
    (repo_path / "README.md").write_text("modified")

    git_manager.add_file("new_file.md")  # Stage one file

    status = git_manager.get_status()
    assert status["files_changed_count"] == 2

    files = {f["path"]: f for f in status["files"]}
    assert files["new_file.md"]["index_status"] == "A"
    assert files["new_file.md"]["work_tree_status"] == " "
    assert files["README.md"]["index_status"] == " "
    assert files["README.md"]["work_tree_status"] == "M"


def test_add_and_commit(git_manager: GitManager):
    """
    Tests the basic add and commit workflow.
    """
    repo_path = Path(git_manager.repo.workdir)
    (repo_path / "feature.md").write_text("A new feature.")

    git_manager.add_file("feature.md")
    commit_info = git_manager.commit("Add feature.md")

    assert "hash" in commit_info
    assert len(commit_info["hash"]) == 40
    assert commit_info["message"] == "Add feature.md"

    # Verify commit exists and is the new HEAD
    head_commit = git_manager.repo.head.peel()
    assert str(head_commit.id) == commit_info["hash"]
    assert "feature.md" in head_commit.tree

    # Verify status is clean after commit
    assert not git_manager.repo.status()


def test_commit_no_changes_raises_error(git_manager: GitManager):
    """
    Tests that committing with no staged changes raises NoChangesError.
    """
    with pytest.raises(NoChangesError):
        git_manager.commit("This should fail")


def test_unstage_file(git_manager: GitManager):
    """
    Tests unstaging a file from the index.
    """
    repo_path = Path(git_manager.repo.workdir)
    (repo_path / "temp.md").write_text("temporary content")

    git_manager.add_file("temp.md")
    assert git_manager.repo.status()["temp.md"] == FileStatus.INDEX_NEW

    git_manager.unstage_file("temp.md")
    assert git_manager.repo.status()["temp.md"] == FileStatus.WT_NEW


def test_discard_file(git_manager: GitManager):
    """
    Tests discarding changes to a modified file.
    """
    readme_path = Path(git_manager.repo.workdir) / "README.md"
    original_content = readme_path.read_text()

    readme_path.write_text("This change should be discarded.")
    assert git_manager.repo.status()["README.md"] == FileStatus.WT_MODIFIED

    git_manager.discard_file("README.md")
    assert not git_manager.repo.status()  # Should be clean
    assert readme_path.read_text() == original_content


def test_add_all_stages_all_changes(git_manager: GitManager):
    """
    Tests that add_all stages new, modified, and deleted files.
    """
    repo_path = Path(git_manager.repo.workdir)
    # Arrange
    (repo_path / "new_file.txt").write_text("new")
    (repo_path / "README.md").write_text("modified")
    make_commit(git_manager.repo, "to_delete.txt", "delete me", "add file to delete")
    (repo_path / "to_delete.txt").unlink()

    # Act
    git_manager.add_all()

    # Assert
    status = git_manager.repo.status()
    assert status["new_file.txt"] == FileStatus.INDEX_NEW
    assert status["README.md"] == FileStatus.INDEX_MODIFIED
    assert status["to_delete.txt"] == FileStatus.INDEX_DELETED


def test_discard_untracked_file_removes_it(git_manager: GitManager):
    """
    Tests that discard_file on a new (untracked) file deletes it from disk.
    """
    new_file_path = Path(git_manager.repo.workdir) / "untracked.md"
    new_file_path.write_text("I am new here.")
    assert new_file_path.exists()

    git_manager.discard_file("untracked.md")

    assert not new_file_path.exists()
    assert not git_manager.repo.status()  # Should remain clean


def test_discard_all_cleans_the_entire_workspace(git_manager: GitManager):
    """
    Tests that discard_all reverts all modifications and removes all untracked files.
    """
    repo_path = Path(git_manager.repo.workdir)
    # Arrange: Create a messy workspace
    (repo_path / "untracked_file.txt").write_text("untracked")
    (repo_path / "untracked_dir").mkdir()
    (repo_path / "untracked_dir" / "nested.txt").write_text("nested")
    (repo_path / "README.md").write_text("This is a modification.")

    # Act
    git_manager.discard_all()

    # Assert
    assert not (repo_path / "untracked_file.txt").exists()
    assert not (repo_path / "untracked_dir").exists()
    assert "Initial commit" in (repo_path / "README.md").read_text()
    assert not git_manager.repo.status()  # Workspace is clean


def test_get_files_in_commit(git_manager: GitManager):
    """
    Tests getting file changes for a commit with add, modify, and delete.
    """
    repo_path = Path(git_manager.repo.workdir)
    # Arrange
    # FIX: Create a proper base state for modification and deletion
    (repo_path / "file_to_modify.txt").write_text("original")
    make_commit(
        git_manager.repo, "file_to_modify.txt", "original", "base: add file to modify"
    )

    (repo_path / "file_to_delete.txt").write_text("delete me")
    make_commit(
        git_manager.repo, "file_to_delete.txt", "delete me", "base: add file to delete"
    )

    # Now, make the changes we want to inspect
    (repo_path / "file_to_add.txt").write_text("new file")
    (repo_path / "file_to_modify.txt").write_text("modified content")
    (repo_path / "file_to_delete.txt").unlink()
    git_manager.add_all()
    commit_info = git_manager.commit("feat: Test complex changes")

    # Act
    files = git_manager.get_files_in_commit(commit_info["hash"])

    # Assert
    statuses = {f["path"]: f["status"] for f in files}
    assert statuses.get("file_to_add.txt") == "A"
    assert statuses.get("file_to_modify.txt") == "M"
    assert statuses.get("file_to_delete.txt") == "D"


def test_get_files_in_initial_commit(git_manager: GitManager):
    """
    Tests getting files for the very first commit in the repository.
    This test verifies that the logic for handling commits with no parents works correctly.
    """
    # Arrange: Find the root commit of the repository.
    # The `repo_with_initial_commit` fixture creates a repo with one commit.
    # We need to find this commit's hash.
    repo = git_manager.repo

    # Walk backwards from HEAD to find the very first commit (the root).
    # This is a robust way to find the initial commit in any test setup.
    walker = repo.walk(repo.head.target, SortMode.TOPOLOGICAL | SortMode.REVERSE)

    try:
        initial_commit = next(walker)
    except StopIteration:
        pytest.fail("Test setup failed: Repository has no commits.")

    initial_commit_hash = str(initial_commit.id)

    # Act: Call the method under test.
    files = git_manager.get_files_in_commit(initial_commit_hash)

    # Assert: Verify the results.

    # 1. We should get a list of files that were added in the initial commit.
    #    The fixture adds 'README.md' and '.gitignore'.
    assert len(files) == 2, "Should find exactly two files in the initial commit."

    # 2. Extract the paths for easier assertion.
    file_info = {f["path"]: f for f in files}

    # 3. Check for the presence of the expected files.
    assert (
        "README.md" in file_info
    ), "README.md should be in the initial commit's file list."
    assert (
        ".gitignore" in file_info
    ), ".gitignore should be in the initial commit's file list."

    # 4. For an initial commit, all files are considered 'Added'.
    #    The status character 'A' is the expected representation.
    #    This assertion is crucial to ensure the diff logic is correct.
    assert file_info["README.md"]["status"] == "A"
    assert file_info[".gitignore"]["status"] == "A"

    # A more concise way to write the same assertion:
    assert all(
        f["status"] == "A" for f in files
    ), "All files in the initial commit should have the status 'A'."


def test_get_files_with_invalid_hash_raises_error(git_manager: GitManager):
    """
    Tests that get_files_in_commit raises an error for a non-existent hash.
    """
    with pytest.raises(pygit2.GitError):
        git_manager.get_files_in_commit("abcdef1234567890abcdef1234567890abcdef12")
