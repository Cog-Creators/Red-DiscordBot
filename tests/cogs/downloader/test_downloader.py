import pathlib
from collections import namedtuple
from pathlib import Path

import pytest
from raven.versioning import fetch_git_sha

from redbot.cogs.downloader.repo_manager import RepoManager, Repo


async def fake_run(*args, **kwargs):
    fake_result_tuple = namedtuple("fake_result", "returncode result")
    res = fake_result_tuple(0, (args, kwargs))
    print(args[0])
    return res


async def fake_run_noprint(*args, **kwargs):
    fake_result_tuple = namedtuple("fake_result", "returncode result")
    res = fake_result_tuple(0, (args, kwargs))
    return res


@pytest.fixture(scope="module", autouse=True)
def patch_relative_to(monkeysession):

    def fake_relative_to(self, some_path: Path):
        return self

    monkeysession.setattr("pathlib.Path.relative_to", fake_relative_to)


@pytest.fixture
def repo_manager(tmpdir_factory, config):
    config.register_global(repos={})
    rm = RepoManager(config)
    # rm.repos_folder = Path(str(tmpdir_factory.getbasetemp())) / 'repos'
    return rm


@pytest.fixture
def repo(tmpdir):
    repo_folder = Path(str(tmpdir)) / "repos" / "squid"
    repo_folder.mkdir(parents=True, exist_ok=True)

    return Repo(
        url="https://github.com/tekulvw/Squid-Plugins",
        name="squid",
        branch="rewrite_cogs",
        folder_path=repo_folder,
    )


@pytest.fixture
def repo_norun(repo):
    repo._run = fake_run
    return repo


@pytest.fixture
def bot_repo(event_loop):
    cwd = Path.cwd()
    return Repo(
        name="Red-DiscordBot",
        branch="WRONG",
        url="https://empty.com/something.git",
        folder_path=cwd,
        loop=event_loop,
    )


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
async def test_clone_repo(repo_norun, capsys):
    await repo_norun.clone()

    clone_cmd, _ = capsys.readouterr()
    clone_cmd = clone_cmd.strip("[']\n").split("', '")
    assert clone_cmd[0] == "git"
    assert clone_cmd[1] == "clone"
    assert clone_cmd[2] == "-b"
    assert clone_cmd[3] == "rewrite_cogs"
    assert clone_cmd[4] == repo_norun.url
    assert ("repos", "squid") == pathlib.Path(clone_cmd[5]).parts[-2:]


@pytest.mark.asyncio
async def test_add_repo(monkeypatch, repo_manager):
    monkeypatch.setattr("redbot.cogs.downloader.repo_manager.Repo._run", fake_run_noprint)

    squid = await repo_manager.add_repo(
        url="https://github.com/tekulvw/Squid-Plugins", name="squid", branch="rewrite_cogs"
    )

    assert squid.available_modules == []


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
