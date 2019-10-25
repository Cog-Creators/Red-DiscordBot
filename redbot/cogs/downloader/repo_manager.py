from __future__ import annotations

import asyncio
import functools
import os
import pkgutil
import shlex
import shutil
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import run as sp_run, PIPE, CompletedProcess
from string import Formatter
from sys import executable
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Dict,
    Generator,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Tuple,
)

import discord
from redbot.core import data_manager, commands, Config
from redbot.core.utils import safe_delete
from redbot.core.i18n import Translator

from . import errors
from .installable import Installable, InstallableType, InstalledModule
from .json_mixins import RepoJSONMixin
from .log import log

_ = Translator("RepoManager", __file__)


class Candidate(NamedTuple):
    rev: str
    object_type: str
    description: str


class _RepoCheckoutCtxManager(
    Awaitable[None], AsyncContextManager[None]
):  # pylint: disable=duplicate-bases
    def __init__(
        self,
        repo: Repo,
        rev: Optional[str],
        exit_to_rev: Optional[str] = None,
        force_checkout: bool = False,
    ):
        self.repo = repo
        self.rev = rev
        if exit_to_rev is None:
            self.exit_to_rev = self.repo.commit
        else:
            self.exit_to_rev = exit_to_rev
        self.force_checkout = force_checkout
        self.coro = repo._checkout(self.rev, force_checkout=self.force_checkout)

    def __await__(self) -> Generator[Any, None, None]:
        return self.coro.__await__()

    async def __aenter__(self) -> None:
        await self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.rev is not None:
            await self.repo._checkout(self.exit_to_rev, force_checkout=self.force_checkout)


class ProcessFormatter(Formatter):
    def vformat(self, format_string, args, kwargs):
        return shlex.split(super().vformat(format_string, args, kwargs))

    def get_value(self, key, args, kwargs):
        obj = super().get_value(key, args, kwargs)
        if isinstance(obj, str) or not isinstance(obj, Iterable):
            return shlex.quote(str(obj))
        return " ".join(shlex.quote(str(o)) for o in obj)


class Repo(RepoJSONMixin):
    GIT_CLONE = "git clone --recurse-submodules -b {branch} {url} {folder}"
    GIT_CLONE_NO_BRANCH = "git clone --recurse-submodules {url} {folder}"
    GIT_CURRENT_BRANCH = "git -C {path} symbolic-ref --short HEAD"
    GIT_CURRENT_COMMIT = "git -C {path} rev-parse HEAD"
    GIT_LATEST_COMMIT = "git -C {path} rev-parse {branch}"
    GIT_HARD_RESET = "git -C {path} reset --hard origin/{branch} -q"
    GIT_PULL = "git -C {path} pull --recurse-submodules -q --ff-only"
    GIT_DIFF_FILE_STATUS = (
        "git -C {path} diff-tree --no-commit-id --name-status"
        " -r -z --line-prefix='\t' {old_rev} {new_rev}"
    )
    GIT_LOG = "git -C {path} log --relative-date --reverse {old_rev}.. {relative_file_path}"
    GIT_DISCOVER_REMOTE_URL = "git -C {path} config --get remote.origin.url"
    GIT_CHECKOUT = "git -C {path} checkout {rev}"
    GIT_GET_FULL_SHA1 = "git -C {path} rev-parse --verify {rev}^{{commit}}"
    GIT_IS_ANCESTOR = (
        "git -C {path} merge-base --is-ancestor {maybe_ancestor_rev} {descendant_rev}"
    )
    GIT_CHECK_IF_MODULE_EXISTS = "git -C {path} cat-file -e {rev}:{module_name}/__init__.py"
    # ↓ this gives a commit after last occurrence
    GIT_GET_LAST_MODULE_OCCURRENCE_COMMIT = (
        "git -C {path} log --diff-filter=D --pretty=format:%H -n 1 {descendant_rev}"
        " -- {module_name}/__init__.py"
    )

    PIP_INSTALL = "{python} -m pip install -U -t {target_dir} {reqs}"

    MODULE_FOLDER_REGEX = re.compile(r"(\w+)\/")
    AMBIGUOUS_ERROR_REGEX = re.compile(
        r"^hint: {3}(?P<rev>[A-Za-z0-9]+) (?P<type>commit|tag) (?P<desc>.+)$", re.MULTILINE
    )

    def __init__(
        self,
        name: str,
        url: str,
        branch: str,
        commit: str,
        folder_path: Path,
        available_modules: Tuple[Installable, ...] = (),
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.url = url
        self.branch = branch
        self.commit = commit

        self.name = name

        self.folder_path = folder_path
        self.folder_path.mkdir(parents=True, exist_ok=True)

        super().__init__(self.folder_path)

        self.available_modules = available_modules

        self._executor = ThreadPoolExecutor(1)

        self._repo_lock = asyncio.Lock()

        self._loop = loop if loop is not None else asyncio.get_event_loop()

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> Repo:
        downloader_cog = ctx.bot.get_cog("Downloader")
        if downloader_cog is None:
            raise commands.CommandError(_("No Downloader cog found."))

        # noinspection PyProtectedMember
        repo_manager = downloader_cog._repo_manager
        poss_repo = repo_manager.get_repo(argument)
        if poss_repo is None:
            raise commands.BadArgument(
                _('Repo by the name "{repo_name}" does not exist.').format(repo_name=argument)
            )
        return poss_repo

    def _existing_git_repo(self) -> Tuple[bool, Path]:
        git_path = self.folder_path / ".git"
        return git_path.exists(), git_path

    async def is_ancestor(self, maybe_ancestor_rev: str, descendant_rev: str) -> bool:
        """
        Check if the first is an ancestor of the second.

        Parameters
        ----------
        maybe_ancestor_rev : `str`
            Revision to check if it is ancestor of :code:`descendant_rev`
        descendant_rev : `str`
            Descendant revision

        Returns
        -------
        bool
            `True` if :code:`maybe_ancestor_rev` is
            ancestor of :code:`descendant_rev` or `False` otherwise

        """
        valid_exit_codes = (0, 1)
        p = await self._run(
            ProcessFormatter().format(
                self.GIT_IS_ANCESTOR,
                path=self.folder_path,
                maybe_ancestor_rev=maybe_ancestor_rev,
                descendant_rev=descendant_rev,
            ),
            valid_exit_codes=valid_exit_codes,
        )

        if p.returncode in valid_exit_codes:
            return not bool(p.returncode)
        raise errors.GitException(
            f"Git failed to determine if commit {maybe_ancestor_rev}"
            f" is ancestor of {descendant_rev} for repo at path: {self.folder_path}"
        )

    async def is_on_branch(self) -> bool:
        """
        Check if repo is currently on branch.

        Returns
        -------
        bool
            `True` if repo is on branch or `False` otherwise

        """
        return await self.latest_commit() == self.commit

    async def _get_file_update_statuses(
        self, old_rev: str, new_rev: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Gets the file update status letters for each changed file between the two revisions.

        Parameters
        ----------
        old_rev : `str`
            Pre-update revision
        new_rev : `str`, optional
            Post-update revision, defaults to repo's branch if not given

        Returns
        -------
        Dict[str, str]
            Mapping of filename -> status_letter

        """
        if new_rev is None:
            new_rev = self.branch
        p = await self._run(
            ProcessFormatter().format(
                self.GIT_DIFF_FILE_STATUS, path=self.folder_path, old_rev=old_rev, new_rev=new_rev
            )
        )

        if p.returncode != 0:
            raise errors.GitDiffError(
                "Git diff failed for repo at path: {}".format(self.folder_path)
            )

        stdout = p.stdout.strip(b"\t\n\x00 ").decode().split("\x00\t")
        ret = {}

        for filename in stdout:
            status, __, filepath = filename.partition("\x00")  # NUL character
            ret[filepath] = status

        return ret

    async def get_last_module_occurrence(
        self, module_name: str, descendant_rev: Optional[str] = None
    ) -> Optional[Installable]:
        """
        Gets module's `Installable` from last commit in which it still occurs.

        Parameters
        ----------
        module_name : str
            Name of module to get.
        descendant_rev : `str`, optional
            Revision from which the module's commit must be
            reachable (i.e. descendant commit),
            defaults to repo's branch if not given.

        Returns
        -------
        `Installable`
            Module from last commit in which it still occurs
            or `None` if it couldn't be found.

        """
        if descendant_rev is None:
            descendant_rev = self.branch
        p = await self._run(
            ProcessFormatter().format(
                self.GIT_CHECK_IF_MODULE_EXISTS,
                path=self.folder_path,
                rev=descendant_rev,
                module_name=module_name,
            ),
            debug_only=True,
        )
        if p.returncode == 0:
            async with self.checkout(descendant_rev):
                return discord.utils.get(self.available_modules, name=module_name)

        p = await self._run(
            ProcessFormatter().format(
                self.GIT_GET_LAST_MODULE_OCCURRENCE_COMMIT,
                path=self.folder_path,
                descendant_rev=descendant_rev,
                module_name=module_name,
            )
        )

        if p.returncode != 0:
            raise errors.GitException(
                "Git log failed for repo at path: {}".format(self.folder_path)
            )

        commit = p.stdout.decode().strip()
        if commit:
            async with self.checkout(f"{commit}~"):
                return discord.utils.get(self.available_modules, name=module_name)
        return None

    async def _is_module_modified(self, module: Installable, other_hash: str) -> bool:
        """
        Checks if given module was different in :code:`other_hash`.

        Parameters
        ----------
        module : `Installable`
            Module to check.
        other_hash : `str`
            Hash to compare module to.

        Returns
        -------
        bool
            `True` if module was different, `False` otherwise.

        """
        if module.commit == other_hash:
            return False

        for status in await self._get_file_update_statuses(other_hash, module.commit):
            match = self.MODULE_FOLDER_REGEX.match(status)
            if match is not None and match.group(1) == module.name:
                return True

        return False

    async def get_modified_modules(
        self, old_rev: str, new_rev: Optional[str] = None
    ) -> Tuple[Installable, ...]:
        """
        Gets modified modules between the two revisions.
        For every module that doesn't exist in :code:`new_rev`,
        it will try to find last commit, where it still existed

        Parameters
        ----------
        old_rev : `str`
            Pre-update revision, ancestor of :code:`new_rev`
        new_rev : `str`, optional
            Post-update revision, defaults to repo's branch if not given

        Returns
        -------
        `tuple` of `Installable`
            List of changed modules between the two revisions.

        """
        if new_rev is None:
            new_rev = self.branch
        modified_modules = set()
        # check differences
        for status in await self._get_file_update_statuses(old_rev, new_rev):
            match = self.MODULE_FOLDER_REGEX.match(status)
            if match is not None:
                modified_modules.add(match.group(1))

        async with self.checkout(old_rev):
            # save old modules
            old_hash = self.commit
            old_modules = self.available_modules
            # save new modules
            await self.checkout(new_rev)
            modules = []
            new_modules = self.available_modules
            for old_module in old_modules:
                if old_module.name not in modified_modules:
                    continue
                try:
                    index = new_modules.index(old_module)
                except ValueError:
                    # module doesn't exist in this revision, try finding previous occurrence
                    module = await self.get_last_module_occurrence(old_module.name, new_rev)
                    if module is not None and await self._is_module_modified(module, old_hash):
                        modules.append(module)
                else:
                    modules.append(new_modules[index])

        return tuple(modules)

    async def _get_commit_notes(self, old_rev: str, relative_file_path: str) -> str:
        """
        Gets the commit notes from git log.
        :param old_rev: Point in time to start getting messages
        :param relative_file_path: Path relative to the repo folder of the file
            to get messages for.
        :return: Git commit note log
        """
        p = await self._run(
            ProcessFormatter().format(
                self.GIT_LOG,
                path=self.folder_path,
                old_rev=old_rev,
                relative_file_path=relative_file_path,
            )
        )

        if p.returncode != 0:
            raise errors.GitException(
                "An exception occurred while executing git log on"
                " this repo: {}".format(self.folder_path)
            )

        return p.stdout.decode().strip()

    async def get_full_sha1(self, rev: str) -> str:
        """
        Gets full sha1 object name.

        Parameters
        ----------
        rev : str
            Revision to search for full sha1 object name.

        Raises
        ------
        .UnknownRevision
            When git cannot find provided revision.
        .AmbiguousRevision
            When git cannot resolve provided short sha1 to one commit.

        Returns
        -------
        `str`
            Full sha1 object name for provided revision.

        """
        p = await self._run(
            ProcessFormatter().format(self.GIT_GET_FULL_SHA1, path=self.folder_path, rev=rev)
        )

        if p.returncode != 0:
            stderr = p.stderr.decode().strip()
            ambiguous_error = f"error: short SHA1 {rev} is ambiguous\nhint: The candidates are:\n"
            if not stderr.startswith(ambiguous_error):
                raise errors.UnknownRevision(f"Revision {rev} cannot be found.")
            candidates = []
            for match in self.AMBIGUOUS_ERROR_REGEX.finditer(stderr, len(ambiguous_error)):
                candidates.append(Candidate(match["rev"], match["type"], match["desc"]))
            if candidates:
                raise errors.AmbiguousRevision(f"Short SHA1 {rev} is ambiguous.", candidates)
            raise errors.UnknownRevision(f"Revision {rev} cannot be found.")

        return p.stdout.decode().strip()

    def _update_available_modules(self) -> Tuple[Installable, ...]:
        """
        Updates the available modules attribute for this repo.
        :return: List of available modules.
        """
        curr_modules = []
        """
        for name in self.folder_path.iterdir():
            if name.is_dir():
                spec = importlib.util.spec_from_file_location(
                    name.stem, location=str(name.parent)
                )
                if spec is not None:
                    curr_modules.append(
                        Installable(location=name)
                    )
        """
        for file_finder, name, is_pkg in pkgutil.iter_modules(path=[str(self.folder_path)]):
            if is_pkg:
                curr_modules.append(
                    Installable(location=self.folder_path / name, repo=self, commit=self.commit)
                )
        self.available_modules = tuple(curr_modules)

        return self.available_modules

    async def _run(
        self,
        *args: Any,
        valid_exit_codes: Tuple[int, ...] = (0,),
        debug_only: bool = False,
        **kwargs: Any,
    ) -> CompletedProcess:
        """
        Parameters
        ----------
        valid_exit_codes : tuple
            Specifies valid exit codes, used to determine
            if stderr should be sent as debug or error level in logging.
            When not provided, defaults to :code:`(0,)`
        debug_only : bool
            Specifies if stderr can be sent only as debug level in logging.
            When not provided, defaults to `False`
        """
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        kwargs["env"] = env
        async with self._repo_lock:
            p: CompletedProcess = await self._loop.run_in_executor(
                self._executor,
                functools.partial(sp_run, *args, stdout=PIPE, stderr=PIPE, **kwargs),
            )
            stderr = p.stderr.decode().strip()
            if stderr:
                if debug_only or p.returncode in valid_exit_codes:
                    log.debug(stderr)
                else:
                    log.error(stderr)
            return p

    async def _setup_repo(self) -> None:
        self.commit = await self.current_commit()
        self._read_info_file()
        self._update_available_modules()

    async def _checkout(self, rev: Optional[str] = None, force_checkout: bool = False) -> None:
        if rev is None:
            return
        if not force_checkout and self.commit == rev:
            return
        exists, __ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            ProcessFormatter().format(self.GIT_CHECKOUT, path=self.folder_path, rev=rev)
        )

        if p.returncode != 0:
            raise errors.UnknownRevision(
                "Could not checkout to {}. This revision may not exist".format(rev)
            )

        await self._setup_repo()

    def checkout(
        self,
        rev: Optional[str] = None,
        *,
        exit_to_rev: Optional[str] = None,
        force_checkout: bool = False,
    ) -> _RepoCheckoutCtxManager:
        """
        Checks out repository to provided revision.

        The return value of this method can also be used as an asynchronous
        context manager, i.e. with :code:`async with` syntax. This will
        checkout repository to :code:`exit_to_rev` on exit of the context manager.

        Parameters
        ----------
        rev : str, optional
            Revision to checkout to, when not provided, method won't do anything
        exit_to_rev : str, optional
            Revision to checkout to after exiting context manager,
            when not provided, defaults to current commit
            This will be ignored, when used with :code:`await` or when :code:`rev` is `None`.
        force_checkout : bool
            When `True` checkout will be done even
            if :code:`self.commit` is the same as target hash
            (applies to exiting context manager as well)
            If provided revision isn't full sha1 hash,
            checkout will be done no matter to this parameter.
            Defaults to `False`.

        Raises
        ------
        .UnknownRevision
            When git cannot checkout to provided revision.

        """

        return _RepoCheckoutCtxManager(self, rev, exit_to_rev, force_checkout)

    async def clone(self) -> Tuple[Installable, ...]:
        """Clone a new repo.

        Returns
        -------
        `tuple` of `str`
            All available module names from this repo.

        """
        exists, path = self._existing_git_repo()
        if exists:
            raise errors.ExistingGitRepo("A git repo already exists at path: {}".format(path))

        if self.branch is not None:
            p = await self._run(
                ProcessFormatter().format(
                    self.GIT_CLONE, branch=self.branch, url=self.url, folder=self.folder_path
                )
            )
        else:
            p = await self._run(
                ProcessFormatter().format(
                    self.GIT_CLONE_NO_BRANCH, url=self.url, folder=self.folder_path
                )
            )

        if p.returncode:
            # Try cleaning up folder
            shutil.rmtree(str(self.folder_path), ignore_errors=True)
            raise errors.CloningError("Error when running git clone.")

        if self.branch is None:
            self.branch = await self.current_branch()

        await self._setup_repo()

        return self.available_modules

    async def current_branch(self) -> str:
        """Determine the current branch using git commands.

        Returns
        -------
        str
            The current branch name.

        """
        exists, __ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            ProcessFormatter().format(self.GIT_CURRENT_BRANCH, path=self.folder_path)
        )

        if p.returncode != 0:
            raise errors.GitException(
                "Could not determine current branch at path: {}".format(self.folder_path)
            )

        return p.stdout.decode().strip()

    async def current_commit(self) -> str:
        """Determine the current commit hash of the repo.

        Returns
        -------
        str
            The requested commit hash.

        """
        exists, __ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            ProcessFormatter().format(self.GIT_CURRENT_COMMIT, path=self.folder_path)
        )

        if p.returncode != 0:
            raise errors.CurrentHashError("Unable to determine commit hash.")

        return p.stdout.decode().strip()

    async def latest_commit(self, branch: Optional[str] = None) -> str:
        """Determine the latest commit hash of the repo.

        Parameters
        ----------
        branch : `str`, optional
            Override for repo's branch attribute.

        Returns
        -------
        str
            The requested commit hash.

        """
        if branch is None:
            branch = self.branch

        exists, __ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            ProcessFormatter().format(self.GIT_LATEST_COMMIT, path=self.folder_path, branch=branch)
        )

        if p.returncode != 0:
            raise errors.CurrentHashError("Unable to determine latest commit hash.")

        return p.stdout.decode().strip()

    async def current_url(self, folder: Optional[Path] = None) -> str:
        """
        Discovers the FETCH URL for a Git repo.

        Parameters
        ----------
        folder : pathlib.Path
            The folder to search for a URL.

        Returns
        -------
        str
            The FETCH URL.

        Raises
        ------
        .NoRemoteURL
            When the folder does not contain a git repo with a FETCH URL.

        """
        if folder is None:
            folder = self.folder_path

        p = await self._run(ProcessFormatter().format(Repo.GIT_DISCOVER_REMOTE_URL, path=folder))

        if p.returncode != 0:
            raise errors.NoRemoteURL("Unable to discover a repo URL.")

        return p.stdout.decode().strip()

    async def hard_reset(self, branch: Optional[str] = None) -> None:
        """Perform a hard reset on the current repo.

        Parameters
        ----------
        branch : `str`, optional
            Override for repo branch attribute.

        """
        if branch is None:
            branch = self.branch

        await self.checkout(branch)
        exists, __ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            ProcessFormatter().format(self.GIT_HARD_RESET, path=self.folder_path, branch=branch)
        )

        if p.returncode != 0:
            raise errors.HardResetError(
                "Some error occurred when trying to"
                " execute a hard reset on the repo at"
                " the following path: {}".format(self.folder_path)
            )

    async def update(self) -> Tuple[str, str]:
        """Update the current branch of this repo.

        Returns
        -------
        `tuple` of `str`
            :py:code`(old commit hash, new commit hash)`

        """
        old_commit = await self.latest_commit()

        await self.hard_reset()

        p = await self._run(ProcessFormatter().format(self.GIT_PULL, path=self.folder_path))

        if p.returncode != 0:
            raise errors.UpdateError(
                "Git pull returned a non zero exit code"
                " for the repo located at path: {}".format(self.folder_path)
            )

        await self._setup_repo()

        return old_commit, self.commit

    async def install_cog(self, cog: Installable, target_dir: Path) -> InstalledModule:
        """Install a cog to the target directory.

        Parameters
        ----------
        cog : Installable
            The package to install.
        target_dir : pathlib.Path
            The target directory for the cog installation.

        Returns
        -------
        `InstalledModule`
            Cog instance.

        Raises
        ------
        .CopyingError
            When cog couldn't be copied.

        """
        if cog not in self.available_cogs:
            raise errors.DownloaderException("That cog does not exist in this repo")

        if not target_dir.is_dir():
            raise ValueError("That target directory is not actually a directory.")

        if not target_dir.exists():
            raise ValueError("That target directory does not exist.")

        if not await cog.copy_to(target_dir=target_dir):
            raise errors.CopyingError("There was an issue during copying of cog's files")

        return InstalledModule.from_installable(cog)

    async def install_libraries(
        self, target_dir: Path, req_target_dir: Path, libraries: Iterable[Installable] = ()
    ) -> Tuple[Tuple[InstalledModule, ...], Tuple[Installable, ...]]:
        """Install shared libraries to the target directory.

        If :code:`libraries` is not specified, all shared libraries in the repo
        will be installed.

        Parameters
        ----------
        target_dir : pathlib.Path
            Directory to install shared libraries to.
        req_target_dir : pathlib.Path
            Directory to install shared library requirements to.
        libraries : `tuple` of `Installable`
            A subset of available libraries.

        Returns
        -------
        tuple
            2-tuple of installed and failed libraries.

        """

        if libraries:
            if not all([i in self.available_libraries for i in libraries]):
                raise ValueError("Some given libraries are not available in this repo.")
        else:
            libraries = self.available_libraries

        if libraries:
            installed = []
            failed = []
            for lib in libraries:
                if not (
                    await self.install_requirements(cog=lib, target_dir=req_target_dir)
                    and await lib.copy_to(target_dir=target_dir)
                ):
                    failed.append(lib)
                else:
                    installed.append(InstalledModule.from_installable(lib))
            return (tuple(installed), tuple(failed))
        return ((), ())

    async def install_requirements(self, cog: Installable, target_dir: Path) -> bool:
        """Install a cog's requirements.

        Requirements will be installed via pip directly into
        :code:`target_dir`.

        Parameters
        ----------
        cog : Installable
            Cog for which to install requirements.
        target_dir : pathlib.Path
            Path to directory  where requirements are to be installed.

        Returns
        -------
        bool
            Success of the installation.

        """
        if not target_dir.is_dir():
            raise ValueError("Target directory is not a directory.")
        target_dir.mkdir(parents=True, exist_ok=True)

        return await self.install_raw_requirements(cog.requirements, target_dir)

    async def install_raw_requirements(
        self, requirements: Iterable[str], target_dir: Path
    ) -> bool:
        """Install a list of requirements using pip.

        Parameters
        ----------
        requirements : `tuple` of `str`
            List of requirement names to install via pip.
        target_dir : pathlib.Path
            Path to directory where requirements are to be installed.

        Returns
        -------
        bool
            Success of the installation

        """
        if not requirements:
            return True

        # TODO: Check and see if any of these modules are already available

        p = await self._run(
            ProcessFormatter().format(
                self.PIP_INSTALL, python=executable, target_dir=target_dir, reqs=requirements
            )
        )

        if p.returncode != 0:
            log.error(
                "Something went wrong when installing"
                " the following requirements:"
                " {}".format(", ".join(requirements))
            )
            return False
        return True

    @property
    def available_cogs(self) -> Tuple[Installable, ...]:
        """`tuple` of `installable` : All available cogs in this Repo.

        This excludes hidden or shared packages.
        """
        # noinspection PyTypeChecker
        return tuple(
            [m for m in self.available_modules if m.type == InstallableType.COG and not m.disabled]
        )

    @property
    def available_libraries(self) -> Tuple[Installable, ...]:
        """`tuple` of `installable` : All available shared libraries in this
        Repo.
        """
        # noinspection PyTypeChecker
        return tuple(
            [m for m in self.available_modules if m.type == InstallableType.SHARED_LIBRARY]
        )

    @classmethod
    async def from_folder(cls, folder: Path, branch: str = "") -> Repo:
        repo = cls(name=folder.stem, url="", branch=branch, commit="", folder_path=folder)
        repo.url = await repo.current_url()
        if branch == "":
            repo.branch = await repo.current_branch()
            repo._update_available_modules()
        else:
            await repo.checkout(repo.branch, force_checkout=True)
        return repo


class RepoManager:

    GITHUB_OR_GITLAB_RE = re.compile(r"https?://git(?:hub)|(?:lab)\.com/")
    TREE_URL_RE = re.compile(r"(?P<tree>/tree)/(?P<branch>\S+)$")

    def __init__(self) -> None:
        self._repos: Dict[str, Repo] = {}
        self.conf = Config.get_conf(self, identifier=170708480, force_registration=True)
        self.conf.register_global(repos={})

    async def initialize(self) -> None:
        await self._load_repos(set_repos=True)

    @property
    def repos_folder(self) -> Path:
        data_folder = data_manager.cog_data_path(self)
        return data_folder / "repos"

    def does_repo_exist(self, name: str) -> bool:
        return name in self._repos

    @staticmethod
    def validate_and_normalize_repo_name(name: str) -> str:
        if not name.isidentifier():
            raise errors.InvalidRepoName("Not a valid Python variable name.")
        return name.lower()

    async def add_repo(self, url: str, name: str, branch: Optional[str] = None) -> Repo:
        """Add and clone a git repository.

        Parameters
        ----------
        url : str
            URL to the git repository.
        name : str
            Internal name of the repository.
        branch : str
            Name of the default branch to checkout into.

        Returns
        -------
        Repo
            New Repo object representing the cloned repository.

        """
        if self.does_repo_exist(name):
            raise errors.ExistingGitRepo(
                "That repo name you provided already exists. Please choose another."
            )

        url, branch = self._parse_url(url, branch)

        # noinspection PyTypeChecker
        r = Repo(
            url=url, name=name, branch=branch, commit="", folder_path=self.repos_folder / name
        )
        await r.clone()
        await self.conf.repos.set_raw(name, value=r.branch)

        self._repos[name] = r

        return r

    def get_repo(self, name: str) -> Optional[Repo]:
        """Get a Repo object for a repository.

        Parameters
        ----------
        name : str
            The name of the repository to retrieve.

        Returns
        -------
        `Repo` or `None`
            Repo object for the repository, if it exists.

        """
        return self._repos.get(name, None)

    @property
    def repos(self) -> Tuple[Repo, ...]:
        return tuple(self._repos.values())

    def get_all_repo_names(self) -> Tuple[str, ...]:
        """Get all repo names.

        Returns
        -------
        `tuple` of `str`
            Repo names.
        """
        # noinspection PyTypeChecker
        return tuple(self._repos.keys())

    def get_all_cogs(self) -> Tuple[Installable, ...]:
        """Get all cogs.

        Returns
        -------
        `tuple` of `Installable`

        """
        all_cogs: List[Installable] = []
        for repo in self._repos.values():
            all_cogs += repo.available_cogs
        return tuple(all_cogs)

    async def delete_repo(self, name: str) -> None:
        """Delete a repository and its folders.

        Parameters
        ----------
        name : str
            The name of the repository to delete.

        Raises
        ------
        .MissingGitRepo
            If the repo does not exist.

        """
        repo = self.get_repo(name)
        if repo is None:
            raise errors.MissingGitRepo("There is no repo with the name {}".format(name))

        safe_delete(repo.folder_path)

        await self.conf.repos.clear_raw(repo.name)
        try:
            del self._repos[name]
        except KeyError:
            pass

    async def update_repo(self, repo_name: str) -> Tuple[Repo, Tuple[str, str]]:
        """Update repo with provided name.

        Parameters
        ----------
        name : str
            The name of the repository to update.

        Returns
        -------
        Tuple[Repo, Tuple[str, str]]
            A 2-`tuple` with Repo object and a 2-`tuple` of `str`
            containing old and new commit hashes.

        """
        repo = self._repos[repo_name]
        old, new = await repo.update()
        return (repo, (old, new))

    async def update_all_repos(self) -> Dict[Repo, Tuple[str, str]]:
        """Call `Repo.update` on all repositories.

        Returns
        -------
        Dict[Repo, Tuple[str, str]]
            A mapping of `Repo` objects that received new commits to
            a 2-`tuple` of `str` containing old and new commit hashes.

        """
        ret = {}
        for repo_name, __ in self._repos.items():
            repo, (old, new) = await self.update_repo(repo_name)
            if old != new:
                ret[repo] = (old, new)
        return ret

    async def _load_repos(self, set_repos: bool = False) -> Dict[str, Repo]:
        ret = {}
        self.repos_folder.mkdir(parents=True, exist_ok=True)
        for folder in self.repos_folder.iterdir():
            if not folder.is_dir():
                continue
            try:
                branch = await self.conf.repos.get_raw(folder.stem, default="")
                ret[folder.stem] = await Repo.from_folder(folder, branch)
                if branch == "":
                    await self.conf.repos.set_raw(folder.stem, value=ret[folder.stem].branch)
            except errors.NoRemoteURL:
                log.warning("A remote URL does not exist for repo %s", folder.stem)
            except errors.DownloaderException as err:
                log.error("Discarding repo %s due to error.", folder.stem, exc_info=err)
                shutil.rmtree(
                    str(folder),
                    onerror=lambda func, path, exc: log.error(
                        "Failed to remove folder %s", path, exc_info=exc
                    ),
                )

        if set_repos:
            self._repos = ret
        return ret

    def _parse_url(self, url: str, branch: Optional[str]) -> Tuple[str, Optional[str]]:
        if self.GITHUB_OR_GITLAB_RE.match(url):
            tree_url_match = self.TREE_URL_RE.search(url)
            if tree_url_match:
                url = url[: tree_url_match.start("tree")]
                if branch is None:
                    branch = tree_url_match["branch"]
        return url, branch
