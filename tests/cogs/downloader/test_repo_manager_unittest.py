import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from redbot.cogs.downloader.repo_manager import RepoManager, errors, Repo


@pytest.mark.asyncio
async def test_add_repo_case_insensitive(tmp_path):
    manager = RepoManager()
    await manager.initialize()

    # Mock Repo.clone so it doesn't actually clone anything
    with patch("redbot.cogs.downloader.repo_manager.Repo.clone", new_callable=AsyncMock):
        # Add repo with uppercase name
        repo1 = await manager.add_repo("https://example.com/repo.git", "TestRepo")

        # Adding same repo with lowercase name should raise ExistingGitRepo
        with pytest.raises(errors.ExistingGitRepo):
            await manager.add_repo("https://example.com/repo.git", "testrepo")

        # Check that repo is stored with lowercase key
        assert "testrepo" in manager._repos
        assert manager._repos["testrepo"] == repo1


@pytest.mark.asyncio
async def test_delete_repo_case_insensitive(tmp_path):
    manager = RepoManager()
    await manager.initialize()

    with patch("redbot.cogs.downloader.repo_manager.Repo.clone", new_callable=AsyncMock):
        await manager.add_repo("https://example.com/repo.git", "MyRepo")

    # Deleting with different casing should succeed
    await manager.delete_repo("myrepo")  # lowercase
    assert "myrepo" not in manager._repos

    # Deleting a non-existent repo should raise MissingGitRepo
    with pytest.raises(errors.MissingGitRepo):
        await manager.delete_repo("myrepo")


@pytest.mark.asyncio
async def test_update_repo_case_insensitive(tmp_path):
    manager = RepoManager()
    await manager.initialize()

    # Mock Repo.update to return fake commit hashes
    fake_update = AsyncMock(return_value=("oldhash", "newhash"))
    with patch("redbot.cogs.downloader.repo_manager.Repo.clone", new_callable=AsyncMock):
        repo = await manager.add_repo("https://example.com/repo.git", "UpdateRepo")
    repo.update = fake_update

    # Call update_repo with different casing
    updated_repo, (old, new) = await manager.update_repo("updaterepo")
    assert updated_repo == repo
    assert old == "oldhash"
    assert new == "newhash"


@pytest.mark.asyncio
async def test_repo_existing_git_repo(tmp_path):
    # Create a Repo instance
    repo = Repo(
        name="TestRepo",
        url="https://example.com/repo.git",
        branch=None,
        commit="",
        folder_path=tmp_path,
    )

    # Case 1: .git folder does not exist
    exists, path = repo._existing_git_repo()
    assert exists is False
    assert path == tmp_path / ".git"

    # Case 2: .git folder exists
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    exists, path = repo._existing_git_repo()
    assert exists is True
    assert path == git_dir
