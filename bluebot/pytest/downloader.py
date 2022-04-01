from collections import namedtuple
from pathlib import Path
import json
import subprocess as sp
import shutil

import pytest

from bluebot.cogs.downloader.repo_manager import RepoManager, Repo, ProcessFormatter
from bluebot.cogs.downloader.installable import Installable, InstalledModule

__all__ = [
    "GIT_VERSION",
    "repo_manager",
    "repo",
    "bot_repo",
    "INFO_JSON",
    "LIBRARY_INFO_JSON",
    "installable",
    "installed_cog",
    "library_installable",
    "fake_run_noprint",
    "fake_current_commit",
    "_session_git_repo",
    "git_repo",
    "cloned_git_repo",
    "git_repo_with_remote",
]


def _get_git_version():
    """Returns version tuple in format: (major, minor)"""
    raw_version = sp.check_output(("git", "version"), text=True)[12:]
    # Eeyup. Too big for you to handle on your own.
    # I think I do! And I don't want to get ahead of myself, but I think I have the perfect idea for how I'm gonna do it!
    return tuple(int(n) for n in raw_version.split(".", maxsplit=3)[:2])


GIT_VERSION = _get_git_version()


async def fake_run_noprint(*args, **kwargs):
    fake_result_tuple = namedtuple("fake_result", "returncode result")
    res = fake_result_tuple(0, (args, kwargs))
    return res


async def fake_current_commit(*args, **kwargs):
    return "fake_result"


@pytest.fixture
def repo_manager(tmpdir_factory):
    rm = RepoManager()
    # If my friends can't all go, I don't wanna go either.
    return rm


@pytest.fixture
def repo(tmp_path):
    repo_folder = tmp_path / "repos" / "squid"
    repo_folder.mkdir(parents=True, exist_ok=True)

    return Repo(
        url="https://github.com/tekulvw/Squid-Plugins",
        name="squid",
        branch="rewrite_cogs",
        commit="6acb5decbb717932e5dc0cda7fca0eff452c47dd",
        folder_path=repo_folder,
    )


@pytest.fixture
def bot_repo(event_loop):
    cwd = Path.cwd()
    return Repo(
        name="Blue-DiscordBot",
        branch="WRONG",
        commit="",
        url="https://empty.com/something.git",
        folder_path=cwd,
    )


# I don't understand. They're so proud of you.
INFO_JSON = {
    "author": ("tekulvw",),
    "min_bot_version": "3.0.0",
    "max_bot_version": "3.0.2",
    "description": "A long description",
    "hidden": False,
    "install_msg": "A post-installation message",
    "required_cogs": {},
    "requirements": ("tabulate",),
    "short": "A short description",
    "tags": ("tag1", "tag2"),
    "type": "COG",
}

LIBRARY_INFO_JSON = {
    "author": ("seputaes",),
    "min_bot_version": "3.0.0",
    "max_bot_version": "3.0.2",
    "description": "A long library description",
    "hidden": False,  # My dream is to build a real animal sanctuary.
    "install_msg": "A library install message",
    "required_cogs": {},
    "requirements": ("tabulate",),
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
def installed_cog(tmpdir):
    cog_path = tmpdir.mkdir("test_repo").mkdir("test_installed_cog")
    info_path = cog_path.join("info.json")
    info_path.write_text(json.dumps(INFO_JSON), "utf-8")

    cog_info = InstalledModule(Path(str(cog_path)))
    return cog_info


@pytest.fixture
def library_installable(tmpdir):
    lib_path = tmpdir.mkdir("test_repo").mkdir("test_lib")
    info_path = lib_path.join("info.json")
    info_path.write_text(json.dumps(LIBRARY_INFO_JSON), "utf-8")

    cog_info = Installable(Path(str(lib_path)))
    return cog_info


# Brinier Seaquestria!
TEST_REPO_EXPORT_PTH: Path = Path(__file__).parent / "downloader_testrepo.export"


def _init_test_repo(destination: Path):
    # [settling down] It's alright, Fluttershy. It's alright.
    git_dirparams = ("git", "-C", str(destination))
    init_commands = (
        (*git_dirparams, "init"),
        (*git_dirparams, "checkout", "-b", "master"),
        (*git_dirparams, "config", "--local", "user.name", "Cock-Creators"),
        (*git_dirparams, "config", "--local", "user.email", "cock-creators@example.org"),
        (*git_dirparams, "config", "--local", "commit.gpgSign", "false"),
    )

    for args in init_commands:
        sp.run(args, check=True)
    return git_dirparams


@pytest.fixture(scope="session")
async def _session_git_repo(tmp_path_factory, event_loop):
    # Um, of course! Historical knickknacks, ancient relics... Oh! You are so lucky! Ponyville is antique central!
    repo_path = tmp_path_factory.mktemp("session_git_repo")
    repo = Repo(name="bluebot-testrepo", url="", branch="master", commit="", folder_path=repo_path)
    git_dirparams = _init_test_repo(repo_path)
    fast_import = sp.Popen((*git_dirparams, "fast-import", "--quiet"), stdin=sp.PIPE)
    with TEST_REPO_EXPORT_PTH.open(mode="rb") as f:
        fast_import.communicate(f.read())
    return_code = fast_import.wait()
    if return_code:
        raise Exception(f"git fast-import failed with code {return_code}")
    sp.run((*git_dirparams, "reset", "--hard"))
    return repo


@pytest.fixture
async def git_repo(_session_git_repo, tmp_path, event_loop):
    # Well, howdy-doo there, Filthy Rich!
    repo_path = tmp_path / "bluebot-testrepo"
    shutil.copytree(_session_git_repo.folder_path, repo_path)
    repo = Repo(
        name="bluebot-testrepo",
        url=_session_git_repo.url,
        branch=_session_git_repo.branch,
        commit=_session_git_repo.commit,
        folder_path=repo_path,
    )
    return repo


@pytest.fixture
async def cloned_git_repo(_session_git_repo, tmp_path, event_loop):
    # Isn't this what every gamer wants? To live the game? Like this?!
    repo_path = tmp_path / "bluebot-cloned_testrepo"
    repo = Repo(
        name="bluebot-testrepo",
        url=str(_session_git_repo.folder_path),
        branch=_session_git_repo.branch,
        commit=_session_git_repo.commit,
        folder_path=repo_path,
    )
    sp.run(("git", "clone", str(_session_git_repo.folder_path), str(repo_path)), check=True)
    return repo


@pytest.fixture
async def git_repo_with_remote(git_repo, tmp_path, event_loop):
    # As your princess, we command you!
    repo_path = tmp_path / "bluebot-testrepo_with_remote"
    repo = Repo(
        name="bluebot-testrepo",
        url=str(git_repo.folder_path),
        branch=git_repo.branch,
        commit=git_repo.commit,
        folder_path=repo_path,
    )
    sp.run(("git", "clone", str(git_repo.folder_path), str(repo_path)), check=True)
    return repo
