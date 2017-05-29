from collections import namedtuple

import pytest
from cogs.downloader.repo_manager import RepoManager
from pathlib import Path


def fake_run(*args, **kwargs):
    fake_result_tuple = namedtuple("fake_result", "returncode result")
    res = fake_result_tuple(lambda: 0, (args, kwargs))
    print(args[0])
    return res


def fake_run_noprint(*args, **kwargs):
    fake_result_tuple = namedtuple("fake_result", "returncode result")
    res = fake_result_tuple(lambda: 0, (args, kwargs))
    return res


@pytest.fixture(scope="module")
def repo_manager(tmpdir_factory, config):
    rm = RepoManager(config)
    rm.repos_folder = Path(str(tmpdir_factory.getbasetemp())) / 'repos'
    return rm


@pytest.fixture
def repo(tmpdir):
    from cogs.downloader.repo_manager import Repo

    repo_folder = Path(str(tmpdir)) / 'repos' / 'squid'
    repo_folder.mkdir(parents=True, exist_ok=True)

    return Repo(
        url="https://github.com/tekulvw/Squid-Plugins",
        name="squid",
        branch="rewrite_cogs",
        folder_path=repo_folder
    )


@pytest.fixture
def repo_norun(repo):
    repo._run = fake_run
    return repo


def test_existing_git_repo(tmpdir):
    from cogs.downloader.repo_manager import Repo

    repo_folder = Path(str(tmpdir)) / 'repos' / 'squid' / '.git'
    repo_folder.mkdir(parents=True, exist_ok=True)

    r = Repo(
        url="https://github.com/tekulvw/Squid-Plugins",
        name="squid",
        branch="rewrite_cogs",
        folder_path=repo_folder.parent
    )

    exists, _ = r._existing_git_repo()

    assert exists is True


@pytest.mark.asyncio
async def test_clone_repo(repo_norun, capsys):
    await repo_norun.clone()

    clone_cmd, _ = capsys.readouterr()

    clone_cmd = clone_cmd.strip().split(' ')
    assert clone_cmd[0] == 'git'
    assert clone_cmd[1] == 'clone'
    assert clone_cmd[2] == '-b'
    assert clone_cmd[3] == 'rewrite_cogs'
    assert clone_cmd[4] == repo_norun.url
    assert clone_cmd[5].endswith('repos/squid')


@pytest.mark.asyncio
async def test_add_repo(monkeypatch, repo_manager):
    monkeypatch.setattr("cogs.downloader.repo_manager.Repo._run",
                        fake_run_noprint)

    squid = await repo_manager.add_repo(
        url="https://github.com/tekulvw/Squid-Plugins",
        name="squid",
        branch="rewrite_cogs"
    )

    assert squid.available_modules == []
