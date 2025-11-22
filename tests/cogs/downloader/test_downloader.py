import asyncio
import json
import pathlib
import shutil
from collections import namedtuple
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, NamedTuple, Optional, Tuple
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockFixture

from redbot.pytest.downloader import *

from redbot.cogs.downloader.downloader import Downloader
from redbot.cogs.downloader.installable import InstalledModule
from redbot.cogs.downloader.repo_manager import Installable
from redbot.cogs.downloader.repo_manager import Candidate, ProcessFormatter, RepoManager, Repo
from redbot.cogs.downloader.errors import (
    AmbiguousRevision,
    ExistingGitRepo,
    GitException,
    UnknownRevision,
)


class FakeCompletedProcess(NamedTuple):
    returncode: int
    stdout: bytes = b""
    stderr: bytes = b""


def _mock_run(
    mocker: MockFixture, repo: Repo, returncode: int, stdout: bytes = b"", stderr: bytes = b""
):
    return mocker.patch.object(
        repo, "_run", autospec=True, return_value=FakeCompletedProcess(returncode, stdout, stderr)
    )


def _mock_setup_repo(mocker: MockFixture, repo: Repo, commit: str):
    def update_commit(*args, **kwargs):
        repo.commit = commit
        return mocker.DEFAULT

    return mocker.patch.object(
        repo, "_setup_repo", autospec=True, side_effect=update_commit, return_value=None
    )


def test_existing_git_repo(tmp_path):
    repo_folder = tmp_path / "repos" / "squid" / ".git"
    repo_folder.mkdir(parents=True, exist_ok=True)

    r = Repo(
        url="https://github.com/tekulvw/Squid-Plugins",
        name="squid",
        branch="rewrite_cogs",
        commit="6acb5decbb717932e5dc0cda7fca0eff452c47dd",
        folder_path=repo_folder.parent,
    )

    exists, git_path = r._existing_git_repo()

    assert exists is True
    assert git_path == repo_folder


ancestor_rev = "c950fc05a540dd76b944719c2a3302da2e2f3090"
descendant_rev = "fb99eb7d2d5bed514efc98fe6686b368f8425745"


@pytest.mark.parametrize(
    "maybe_ancestor_rev,descendant_rev,returncode,expected",
    [(ancestor_rev, descendant_rev, 0, True), (descendant_rev, ancestor_rev, 1, False)],
)
async def test_is_ancestor(mocker, repo, maybe_ancestor_rev, descendant_rev, returncode, expected):
    m = _mock_run(mocker, repo, returncode)
    ret = await repo.is_ancestor(maybe_ancestor_rev, descendant_rev)
    m.assert_called_once_with(
        ProcessFormatter().format(
            repo.GIT_IS_ANCESTOR,
            path=repo.folder_path,
            maybe_ancestor_rev=maybe_ancestor_rev,
            descendant_rev=descendant_rev,
        ),
        valid_exit_codes=(0, 1),
        debug_only=True,
    )
    assert ret is expected


async def test_is_ancestor_object_raise(mocker, repo):
    m = _mock_run(mocker, repo, 128, b"", b"fatal: Not a valid object name invalid1")
    with pytest.raises(UnknownRevision):
        await repo.is_ancestor("invalid1", "invalid2")

    m.assert_called_once_with(
        ProcessFormatter().format(
            repo.GIT_IS_ANCESTOR,
            path=repo.folder_path,
            maybe_ancestor_rev="invalid1",
            descendant_rev="invalid2",
        ),
        valid_exit_codes=(0, 1),
        debug_only=True,
    )


async def test_is_ancestor_commit_raise(mocker, repo):
    m = _mock_run(
        mocker,
        repo,
        128,
        b"",
        b"fatal: Not a valid commit name 0123456789abcde0123456789abcde0123456789",
    )
    with pytest.raises(UnknownRevision):
        await repo.is_ancestor(
            "0123456789abcde0123456789abcde0123456789", "c950fc05a540dd76b944719c2a3302da2e2f3090"
        )

    m.assert_called_once_with(
        ProcessFormatter().format(
            repo.GIT_IS_ANCESTOR,
            path=repo.folder_path,
            maybe_ancestor_rev="0123456789abcde0123456789abcde0123456789",
            descendant_rev="c950fc05a540dd76b944719c2a3302da2e2f3090",
        ),
        valid_exit_codes=(0, 1),
        debug_only=True,
    )


async def test_get_file_update_statuses(mocker, repo):
    old_rev = "c950fc05a540dd76b944719c2a3302da2e2f3090"
    new_rev = "fb99eb7d2d5bed514efc98fe6686b368f8425745"
    m = _mock_run(
        mocker,
        repo,
        0,
        b"A\x00added_file.txt\x00\t"
        b"M\x00mycog/__init__.py\x00\t"
        b"D\x00sample_file1.txt\x00\t"
        b"D\x00sample_file2.txt\x00\t"
        b"A\x00sample_file3.txt",
    )
    ret = await repo._get_file_update_statuses(old_rev, new_rev)
    m.assert_called_once_with(
        ProcessFormatter().format(
            repo.GIT_DIFF_FILE_STATUS, path=repo.folder_path, old_rev=old_rev, new_rev=new_rev
        )
    )

    assert ret == {
        "added_file.txt": "A",
        "mycog/__init__.py": "M",
        "sample_file1.txt": "D",
        "sample_file2.txt": "D",
        "sample_file3.txt": "A",
    }


async def test_is_module_modified(mocker, repo):
    old_rev = "c950fc05a540dd76b944719c2a3302da2e2f3090"
    new_rev = "fb99eb7d2d5bed514efc98fe6686b368f8425745"
    FakeInstallable = namedtuple("Installable", "name commit")
    module = FakeInstallable("mycog", new_rev)
    m = mocker.patch.object(
        repo,
        "_get_file_update_statuses",
        autospec=True,
        return_value={
            "added_file.txt": "A",
            "mycog/__init__.py": "M",
            "sample_file1.txt": "D",
            "sample_file2.txt": "D",
            "sample_file3.txt": "A",
        },
    )
    ret = await repo._is_module_modified(module, old_rev)
    m.assert_called_once_with(old_rev, new_rev)

    assert ret is True


async def test_get_full_sha1_success(mocker, repo):
    commit = "c950fc05a540dd76b944719c2a3302da2e2f3090"
    m = _mock_run(mocker, repo, 0, commit.encode())
    ret = await repo.get_full_sha1(commit)
    m.assert_called_once_with(
        ProcessFormatter().format(repo.GIT_GET_FULL_SHA1, path=repo.folder_path, rev=commit)
    )

    assert ret == commit


async def test_get_full_sha1_notfound(mocker, repo):
    m = _mock_run(mocker, repo, 128, b"", b"fatal: Needed a single revision")
    with pytest.raises(UnknownRevision):
        await repo.get_full_sha1("invalid")
    m.assert_called_once_with(
        ProcessFormatter().format(repo.GIT_GET_FULL_SHA1, path=repo.folder_path, rev="invalid")
    )


async def test_get_full_sha1_ambiguous(mocker, repo):
    m = _mock_run(
        mocker,
        repo,
        128,
        b"",
        b"error: short SHA1 c6f0 is ambiguous\n"
        b"hint: The candidates are:\n"
        b"hint:   c6f028f tag ambiguous_tag_66387\n"
        b"hint:   c6f0e5e commit 2019-10-24 - Commit ambiguous with tag.\n"
        b"fatal: Needed a single revision",
    )
    with pytest.raises(AmbiguousRevision) as exc_info:
        await repo.get_full_sha1("c6f0")
    m.assert_called_once_with(
        ProcessFormatter().format(repo.GIT_GET_FULL_SHA1, path=repo.folder_path, rev="c6f0")
    )

    assert exc_info.value.candidates == [
        Candidate("c6f028f", "tag", "ambiguous_tag_66387"),
        Candidate("c6f0e5e", "commit", "2019-10-24 - Commit ambiguous with tag."),
    ]


def test_update_available_modules(repo):
    module = repo.folder_path / "mycog" / "__init__.py"
    submodule = module.parent / "submodule" / "__init__.py"
    module.parent.mkdir(parents=True)
    module.touch()
    submodule.parent.mkdir()
    submodule.touch()
    ret = repo._update_available_modules()
    assert (
        ret
        == repo.available_modules
        == (Installable(location=module.parent, repo=repo, commit=repo.commit),)
    )


async def test_checkout(mocker, repo):
    commit = "c950fc05a540dd76b944719c2a3302da2e2f3090"
    m = _mock_run(mocker, repo, 0)
    _mock_setup_repo(mocker, repo, commit)
    git_path = repo.folder_path / ".git"
    git_path.mkdir()
    await repo._checkout(commit)

    assert repo.commit == commit
    m.assert_called_once_with(
        ProcessFormatter().format(repo.GIT_CHECKOUT, path=repo.folder_path, rev=commit)
    )


async def test_checkout_ctx_manager(mocker, repo):
    commit = "c950fc05a540dd76b944719c2a3302da2e2f3090"
    m = mocker.patch.object(repo, "_checkout", autospec=True, return_value=None)
    old_commit = repo.commit
    async with repo.checkout(commit):
        m.assert_called_with(commit, force_checkout=False)
        m.return_value = None

    m.assert_called_with(old_commit, force_checkout=False)


async def test_checkout_await(mocker, repo):
    commit = "c950fc05a540dd76b944719c2a3302da2e2f3090"
    m = mocker.patch.object(repo, "_checkout", autospec=True, return_value=None)
    await repo.checkout(commit)

    m.assert_called_once_with(commit, force_checkout=False)


async def test_clone_with_branch(mocker, repo):
    branch = repo.branch = "dont_add_commits"
    commit = "a0ccc2390883c85a361f5a90c72e1b07958939fa"
    repo.commit = ""
    m = _mock_run(mocker, repo, 0)
    _mock_setup_repo(mocker, repo, commit)

    await repo.clone()

    assert repo.commit == commit
    m.assert_called_once_with(
        ProcessFormatter().format(
            repo.GIT_CLONE, branch=branch, url=repo.url, folder=repo.folder_path
        )
    )


async def test_clone_without_branch(mocker, repo):
    branch = "dont_add_commits"
    commit = "a0ccc2390883c85a361f5a90c72e1b07958939fa"
    repo.branch = None
    repo.commit = ""
    m = _mock_run(mocker, repo, 0)
    _mock_setup_repo(mocker, repo, commit)
    mocker.patch.object(repo, "current_branch", autospec=True, return_value=branch)

    await repo.clone()

    assert repo.commit == commit
    m.assert_called_once_with(
        ProcessFormatter().format(repo.GIT_CLONE_NO_BRANCH, url=repo.url, folder=repo.folder_path)
    )


async def test_update(mocker, repo):
    old_commit = repo.commit
    new_commit = "a0ccc2390883c85a361f5a90c72e1b07958939fa"
    m = _mock_run(mocker, repo, 0)
    _mock_setup_repo(mocker, repo, new_commit)
    mocker.patch.object(repo, "latest_commit", autospec=True, return_value=old_commit)
    mocker.patch.object(repo, "hard_reset", autospec=True, return_value=None)
    ret = await repo.update()

    assert ret == (old_commit, new_commit)
    m.assert_called_once_with(ProcessFormatter().format(repo.GIT_PULL, path=repo.folder_path))


# old tests


async def test_add_repo(monkeypatch, repo_manager):
    monkeypatch.setattr("redbot.cogs.downloader.repo_manager.Repo._run", fake_run_noprint)
    monkeypatch.setattr(
        "redbot.cogs.downloader.repo_manager.Repo.current_commit", fake_current_commit
    )

    squid = await repo_manager.add_repo(
        url="https://github.com/tekulvw/Squid-Plugins", name="squid", branch="rewrite_cogs"
    )

    assert squid.available_modules == ()


async def test_lib_install_requirements(monkeypatch, library_installable, repo, tmpdir):
    monkeypatch.setattr("redbot.cogs.downloader.repo_manager.Repo._run", fake_run_noprint)
    monkeypatch.setattr(
        "redbot.cogs.downloader.repo_manager.Repo.available_libraries", (library_installable,)
    )

    lib_path = Path(str(tmpdir)) / "cog_data_path" / "lib"
    sharedlib_path = lib_path / "cog_shared"
    sharedlib_path.mkdir(parents=True, exist_ok=True)

    installed, failed = await repo.install_libraries(
        target_dir=sharedlib_path, req_target_dir=lib_path
    )

    assert len(installed) == 1
    assert len(failed) == 0


async def test_remove_repo(monkeypatch, repo_manager):
    monkeypatch.setattr("redbot.cogs.downloader.repo_manager.Repo._run", fake_run_noprint)
    monkeypatch.setattr(
        "redbot.cogs.downloader.repo_manager.Repo.current_commit", fake_current_commit
    )

    await repo_manager.add_repo(
        url="https://github.com/tekulvw/Squid-Plugins", name="squid", branch="rewrite_cogs"
    )
    assert repo_manager.get_repo("squid") is not None
    await repo_manager.delete_repo("squid")
    assert repo_manager.get_repo("squid") is None


async def test_requirements_reinstalled_when_info_changes(tmp_path):
    repo_name = "x26-Cogs"
    cog_name = "defender"
    workspace_root = Path(__file__).resolve().parents[4]
    source_repo = workspace_root / repo_name / cog_name
    if not source_repo.exists():
        pytest.skip("x26-Cogs repository is required for this test.")

    repo_path = tmp_path / repo_name
    repo_path.mkdir(parents=True, exist_ok=True)
    cog_path = repo_path / cog_name
    shutil.copytree(source_repo, cog_path)
    info_path = cog_path / "info.json"
    original_info = json.loads(info_path.read_text("utf-8"))

    def _info_with_emoji(version: str) -> Dict[str, Any]:
        info_copy = dict(original_info)
        requirements = list(original_info.get("requirements", ()))
        info_copy["requirements"] = [
            f"emoji=={version}" if req.startswith("emoji") else req for req in requirements
        ]
        return info_copy

    class DummyConfig:
        def __init__(self):
            self.data = {"installed_cogs": {}, "installed_libraries": {}}

        async def installed_libraries(self):
            return self.data["installed_libraries"]

        async def installed_cogs(self):
            return self.data["installed_cogs"]

        @asynccontextmanager
        async def all(self):
            yield self.data

    class DummyRepo:
        def __init__(self):
            self.available_libraries = ()
            self.commit = "new"
            self.name = repo_name
            self.folder_path = repo_path
            self.modified_module: Optional[InstalledModule] = None

        async def get_last_module_occurrence(self, module_name):
            if module_name == cog_name:
                return self.modified_module
            return None

        async def is_ancestor(self, old_commit, new_commit):
            return True

        async def get_modified_modules(self, old_hash, new_hash):
            return (self.modified_module,)

        async def install_raw_requirements(self, requirements, target_dir):
            target_dir.mkdir(parents=True, exist_ok=True)
            for req in requirements:
                if req.startswith("emoji=="):
                    for existing in target_dir.glob("emoji==*"):
                        existing.unlink()
                (target_dir / req).write_text("", encoding="utf-8")
            return True

    class DummyRepoManager:
        def __init__(self, repo):
            self.repos = [repo]
            self.repo = repo
            self.repos_folder = repo.folder_path.parent

        def get_repo(self, name):
            if name == self.repo.name:
                return self.repo
            return None

        async def update_repos(self, repos=None):
            return ({}, [])

    dummy_repo = DummyRepo()
    info_path.write_text(json.dumps(_info_with_emoji("1.6.3")), "utf-8")
    installed = InstalledModule(
        location=cog_path,
        repo=dummy_repo,
        commit="old",
        json_repo_name=repo_name,
    )
    assert "emoji==1.6.3" in installed.requirements

    downloader = Downloader.__new__(Downloader)
    downloader.LIB_PATH = tmp_path / "libs"
    downloader.LIB_PATH.mkdir(parents=True, exist_ok=True)
    downloader.SHAREDLIB_PATH = tmp_path / "shared_libs"
    downloader.SHAREDLIB_PATH.mkdir(parents=True, exist_ok=True)
    downloader._repo_manager = DummyRepoManager(dummy_repo)
    downloader.config = DummyConfig()
    downloader.config.data["installed_cogs"] = {repo_name: {cog_name: installed.to_json()}}
    downloader.config.data["installed_libraries"] = {}
    bot = SimpleNamespace(
        list_enabled_app_commands=AsyncMock(return_value={}),
        extensions={},
        wait_for=AsyncMock(),
        get_cog=lambda name: None,
    )
    downloader.bot = bot

    def installed_emoji_versions() -> Tuple[str, ...]:
        return tuple(sorted(path.name for path in downloader.LIB_PATH.glob("emoji==*")))

    await downloader._install_requirements((installed,))

    info_path.write_text(json.dumps(_info_with_emoji("1.7.0")), "utf-8")
    dummy_repo.modified_module = InstalledModule(
        location=cog_path,
        repo=dummy_repo,
        commit=dummy_repo.commit,
        json_repo_name=repo_name,
    )

    cogs_to_update, libs_to_update = await downloader._available_updates({installed})

    assert len(cogs_to_update) == 1
    updated_installable = cogs_to_update[0]
    assert updated_installable.requirements != installed.requirements
    assert "emoji==1.7.0" in updated_installable.requirements
    assert not libs_to_update

    new_installations = tuple(InstalledModule.from_installable(cog) for cog in cogs_to_update)
    downloader._install_cogs = AsyncMock(return_value=(new_installations, ()))
    downloader._reinstall_libraries = AsyncMock(return_value=((), ()))

    class DummyCtx:
        def __init__(self, bot):
            self.bot = bot
            self.clean_prefix = "[p]"
            self.prefix = "[p]"
            self.assume_yes = True
            self.sent_messages = []

        async def send(self, message):
            self.sent_messages.append(message)

        @asynccontextmanager
        async def typing(self):
            yield

    ctx = DummyCtx(bot)
    assert installed_emoji_versions() == ("emoji==1.6.3",)
    await downloader._cog_update.callback(downloader, ctx, False, installed)
    assert installed_emoji_versions() == ("emoji==1.7.0",)


async def test_existing_repo(mocker, repo_manager):
    repo_manager.does_repo_exist = mocker.MagicMock(return_value=True)

    with pytest.raises(ExistingGitRepo):
        await repo_manager.add_repo("http://test.com", "test")

    repo_manager.does_repo_exist.assert_called_once_with("test")


def test_tree_url_parse(repo_manager):
    cases = [
        {
            "input": ("https://github.com/Tobotimus/Tobo-Cogs", None),
            "expected": ("https://github.com/Tobotimus/Tobo-Cogs", None),
        },
        {
            "input": ("https://github.com/Tobotimus/Tobo-Cogs", "V3"),
            "expected": ("https://github.com/Tobotimus/Tobo-Cogs", "V3"),
        },
        {
            "input": ("https://github.com/Tobotimus/Tobo-Cogs/tree/V3", None),
            "expected": ("https://github.com/Tobotimus/Tobo-Cogs", "V3"),
        },
        {
            "input": ("https://github.com/Tobotimus/Tobo-Cogs/tree/V3", "V4"),
            "expected": ("https://github.com/Tobotimus/Tobo-Cogs", "V4"),
        },
    ]

    for test_case in cases:
        assert test_case["expected"] == repo_manager._parse_url(*test_case["input"])


def test_tree_url_non_github(repo_manager):
    cases = [
        {
            "input": ("https://gitlab.com/Tobotimus/Tobo-Cogs", None),
            "expected": ("https://gitlab.com/Tobotimus/Tobo-Cogs", None),
        },
        {
            "input": ("https://my.usgs.gov/bitbucket/scm/Tobotimus/Tobo-Cogs", "V3"),
            "expected": ("https://my.usgs.gov/bitbucket/scm/Tobotimus/Tobo-Cogs", "V3"),
        },
    ]

    for test_case in cases:
        assert test_case["expected"] == repo_manager._parse_url(*test_case["input"])
