import pathlib
from collections import namedtuple
from pathlib import Path

import pytest
from unittest.mock import MagicMock
from raven.versioning import fetch_git_sha

from redbot.pytest.downloader import *

from redbot.cogs.downloader.repo_manager import RepoManager, Repo
from redbot.cogs.downloader.errors import ExistingGitRepo


def test_existing_git_repo(tmpdir):
    repo_folder = Path(str(tmpdir)) / "repos" / "squid" / ".git"
    repo_folder.mkdir(parents=True, exist_ok=True)

    r = Repo(
        url="https://github.com/tekulvw/Squid-Plugins",
        name="squid",
        branch="rewrite_cogs",
        folder_path=repo_folder.parent,
    )

    exists, _ = r._existing_git_repo()

    assert exists is True


@pytest.mark.asyncio
async def test_add_repo(monkeypatch, repo_manager):
    monkeypatch.setattr("redbot.cogs.downloader.repo_manager.Repo._run", fake_run_noprint)

    squid = await repo_manager.add_repo(
        url="https://github.com/tekulvw/Squid-Plugins", name="squid", branch="rewrite_cogs"
    )

    assert squid.available_modules == []


@pytest.mark.asyncio
async def test_remove_repo(monkeypatch, repo_manager):
    monkeypatch.setattr("redbot.cogs.downloader.repo_manager.Repo._run", fake_run_noprint)

    await repo_manager.add_repo(
        url="https://github.com/tekulvw/Squid-Plugins", name="squid", branch="rewrite_cogs"
    )
    assert repo_manager.get_repo("squid") is not None
    await repo_manager.delete_repo("squid")
    assert repo_manager.get_repo("squid") is None


@pytest.mark.asyncio
async def test_current_branch(bot_repo):
    branch = await bot_repo.current_branch()

    # So this does work, just not sure how to fully automate the test

    assert branch not in ("WRONG", "")


@pytest.mark.asyncio
async def test_current_hash(bot_repo):
    branch = await bot_repo.current_branch()
    bot_repo.branch = branch

    commit = await bot_repo.current_commit()

    sentry_sha = fetch_git_sha(str(bot_repo.folder_path))

    assert sentry_sha == commit


@pytest.mark.asyncio
async def test_existing_repo(repo_manager):
    repo_manager.does_repo_exist = MagicMock(return_value=True)

    with pytest.raises(ExistingGitRepo):
        await repo_manager.add_repo("http://test.com", "test")

    repo_manager.does_repo_exist.assert_called_once_with("test")
