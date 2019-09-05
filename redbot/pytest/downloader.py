# Standard Library
import json

from collections import namedtuple
from pathlib import Path

# Red Dependencies
import pytest

# Red Imports
from redbot.cogs.downloader.installable import Installable
from redbot.cogs.downloader.repo_manager import Repo, RepoManager

__all__ = [
    "patch_relative_to",
    "repo_manager",
    "repo",
    "repo_norun",
    "bot_repo",
    "INFO_JSON",
    "LIBRARY_INFO_JSON",
    "installable",
    "library_installable",
    "fake_run_noprint",
]


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
def repo_manager(tmpdir_factory):
    rm = RepoManager()
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


# Installable
INFO_JSON = {
    "author": ("tekulvw",),
    "min_bot_version": "3.0.0",
    "max_bot_version": "3.0.2",
    "description": "A long description",
    "hidden": False,
    "install_msg": "A post-installation message",
    "required_cogs": {},
    "requirements": "tabulate",
    "short": "A short description",
    "tags": ("tag1", "tag2"),
    "type": "COG",
}

LIBRARY_INFO_JSON = {
    "author": ("seputaes",),
    "min_bot_version": "3.0.0",
    "max_bot_version": "3.0.2",
    "description": "A long library description",
    "hidden": False,  # libraries are always hidden, this tests it will be flipped
    "install_msg": "A library install message",
    "required_cogs": {},
    "requirements": "tabulate",
    "short": "A short library description",
    "tags": ("libtag1", "libtag2"),
    "type": "SHARED_LIBRARY",
}


@pytest.fixture
def installable(tmpdir):
    cog_path = tmpdir.mkdir("test_repo").mkdir("test_cog")
    info_path = cog_path.join("info.json")
    info_path.write_text(json.dumps(INFO_JSON), "utf-8")

    cog_info = Installable(Path(str(cog_path)))
    return cog_info


@pytest.fixture
def library_installable(tmpdir):
    lib_path = tmpdir.mkdir("test_repo").mkdir("test_lib")
    info_path = lib_path.join("info.json")
    info_path.write_text(json.dumps(LIBRARY_INFO_JSON), "utf-8")

    cog_info = Installable(Path(str(lib_path)))
    return cog_info
