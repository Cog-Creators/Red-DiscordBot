import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from redbot.cogs.downloader.repo_manager import RepoManager
from redbot.cogs.downloader import errors

@pytest.mark.asyncio
async def test_repo_case_insensitive(tmp_path):
    manager = RepoManager()
    manager.folder_path = tmp_path

    # Mock add_repo to raise ExistingGitRepo on duplicate (case-insensitive)
    async def fake_add_repo(url, name, branch=None):
        key = name.lower()
        if key in manager._repos:
            raise errors.ExistingGitRepo(
                "That repo name you provided already exists. Please choose another."
            )
        (tmp_path / key).mkdir(parents=True, exist_ok=True)
        manager._repos[key] = object()
        return manager._repos[key]

    # Mock delete_repo to delete using lowercase keys
    async def fake_delete_repo(name):
        key = name.lower()
        if key not in manager._repos:
            raise errors.MissingGitRepo(f"There is no repo with the name {name}")
        del manager._repos[key]
        folder = tmp_path / key
        if folder.exists():
            for child in folder.iterdir():
                if child.is_file():
                    child.unlink()
            folder.rmdir()

    manager.add_repo = AsyncMock(side_effect=fake_add_repo)
    manager.delete_repo = AsyncMock(side_effect=fake_delete_repo)

    # Add repo with uppercase name
    await manager.add_repo("https://example.com/repo.git", "TestRepo")

    # Trying to add the same repo with different casing should now fail
    with pytest.raises(errors.ExistingGitRepo):
        await manager.add_repo("https://example.com/repo.git", "testrepo")

    # Check that get_repo works case-insensitively
    assert manager.get_repo("TestRepo") is not None
    assert manager.get_repo("testrepo") is not None

    # Delete repo using different casing
    await manager.delete_repo("testrepo")

    # Now repo should not exist in any casing
    assert manager.get_repo("TestRepo") is None
    assert manager.get_repo("testrepo") is None
