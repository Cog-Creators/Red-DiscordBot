import asyncio
import functools
import os
import pkgutil
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from subprocess import run as sp_run, PIPE
from sys import executable
from typing import Tuple, MutableMapping, Union

from redbot.core import data_manager, commands
from redbot.core.utils import safe_delete
from . import errors
from .installable import Installable, InstallableType
from .json_mixins import RepoJSONMixin
from .log import log


class Repo(RepoJSONMixin):
    GIT_CLONE = "git clone --recurse-submodules -b {branch} {url} {folder}"
    GIT_CLONE_NO_BRANCH = "git clone --recurse-submodules {url} {folder}"
    GIT_CURRENT_BRANCH = "git -C {path} rev-parse --abbrev-ref HEAD"
    GIT_LATEST_COMMIT = "git -C {path} rev-parse {branch}"
    GIT_HARD_RESET = "git -C {path} reset --hard origin/{branch} -q"
    GIT_PULL = "git -C {path}  --recurse-submodules=yes -q --ff-only"
    GIT_DIFF_FILE_STATUS = "git -C {path} diff --no-commit-id --name-status {old_hash} {new_hash}"
    GIT_LOG = "git -C {path} log --relative-date --reverse {old_hash}.. {relative_file_path}"
    GIT_DISCOVER_REMOTE_URL = "git -C {path} config --get remote.origin.url"

    PIP_INSTALL = "{python} -m pip install -U -t {target_dir} {reqs}"

    def __init__(
        self,
        name: str,
        url: str,
        branch: str,
        folder_path: Path,
        available_modules: Tuple[Installable] = (),
        loop: asyncio.AbstractEventLoop = None,
    ):
        self.url = url
        self.branch = branch

        self.name = name

        self.folder_path = folder_path
        self.folder_path.mkdir(parents=True, exist_ok=True)

        super().__init__(self.folder_path)

        self.available_modules = available_modules

        self._executor = ThreadPoolExecutor(1)

        self._repo_lock = asyncio.Lock()

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str):
        downloader_cog = ctx.bot.get_cog("Downloader")
        if downloader_cog is None:
            raise commands.CommandError("No Downloader cog found.")

        # noinspection PyProtectedMember
        repo_manager = downloader_cog._repo_manager
        poss_repo = repo_manager.get_repo(argument)
        if poss_repo is None:
            raise commands.BadArgument("Repo by the name {} does not exist.".format(argument))
        return poss_repo

    def _existing_git_repo(self) -> (bool, Path):
        git_path = self.folder_path / ".git"
        return git_path.exists(), git_path

    async def _get_file_update_statuses(
        self, old_hash: str, new_hash: str
    ) -> MutableMapping[str, str]:
        """
        Gets the file update status letters for each changed file between
            the two hashes.
        :param old_hash: Pre-update
        :param new_hash: Post-update
        :return: Mapping of filename -> status_letter
        """
        p = await self._run(
            self.GIT_DIFF_FILE_STATUS.format(
                path=self.folder_path, old_hash=old_hash, new_hash=new_hash
            )
        )

        if p.returncode != 0:
            raise errors.GitDiffError(
                "Git diff failed for repo at path: {}".format(self.folder_path)
            )

        stdout = p.stdout.strip().decode().split("\n")

        ret = {}

        for filename in stdout:
            # TODO: filter these filenames by ones in self.available_modules
            status, _, filepath = filename.partition("\t")
            ret[filepath] = status

        return ret

    async def _get_commit_notes(self, old_commit_hash: str, relative_file_path: str) -> str:
        """
        Gets the commit notes from git log.
        :param old_commit_hash: Point in time to start getting messages
        :param relative_file_path: Path relative to the repo folder of the file
            to get messages for.
        :return: Git commit note log
        """
        p = await self._run(
            self.GIT_LOG.format(
                path=self.folder_path,
                old_hash=old_commit_hash,
                relative_file_path=relative_file_path,
            )
        )

        if p.returncode != 0:
            raise errors.GitException(
                "An exception occurred while executing git log on"
                " this repo: {}".format(self.folder_path)
            )

        return p.stdout.decode().strip()

    def _update_available_modules(self) -> Tuple[str]:
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
        for file_finder, name, is_pkg in pkgutil.walk_packages(
            path=[str(self.folder_path)], onerror=lambda name: None
        ):
            if is_pkg:
                curr_modules.append(Installable(location=self.folder_path / name))
        self.available_modules = curr_modules

        # noinspection PyTypeChecker
        return tuple(self.available_modules)

    async def _run(self, *args, **kwargs):
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        kwargs["env"] = env
        async with self._repo_lock:
            return await self._loop.run_in_executor(
                self._executor,
                functools.partial(sp_run, *args, stdout=PIPE, **kwargs),
            )

    async def clone(self) -> Tuple[str]:
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
                self.GIT_CLONE.format(
                    branch=self.branch, url=self.url, folder=self.folder_path
                ).split()
            )
        else:
            p = await self._run(
                self.GIT_CLONE_NO_BRANCH.format(url=self.url, folder=self.folder_path).split()
            )

        if p.returncode:
            # Try cleaning up folder
            shutil.rmtree(str(self.folder_path), ignore_errors=True)
            raise errors.CloningError("Error when running git clone.")

        if self.branch is None:
            self.branch = await self.current_branch()

        self._read_info_file()

        return self._update_available_modules()

    async def current_branch(self) -> str:
        """Determine the current branch using git commands.

        Returns
        -------
        str
            The current branch name.

        """
        exists, _ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(self.GIT_CURRENT_BRANCH.format(path=self.folder_path).split())

        if p.returncode != 0:
            raise errors.GitException(
                "Could not determine current branch at path: {}".format(self.folder_path)
            )

        return p.stdout.decode().strip()

    async def current_commit(self, branch: str = None) -> str:
        """Determine the current commit hash of the repo.

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

        exists, _ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            self.GIT_LATEST_COMMIT.format(path=self.folder_path, branch=branch).split()
        )

        if p.returncode != 0:
            raise errors.CurrentHashError("Unable to determine old commit hash.")

        return p.stdout.decode().strip()

    async def current_url(self, folder: Path = None) -> str:
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

        p = await self._run(Repo.GIT_DISCOVER_REMOTE_URL.format(path=folder).split())

        if p.returncode != 0:
            raise errors.NoRemoteURL("Unable to discover a repo URL.")

        return p.stdout.decode().strip()

    async def hard_reset(self, branch: str = None) -> None:
        """Perform a hard reset on the current repo.

        Parameters
        ----------
        branch : `str`, optional
            Override for repo branch attribute.

        """
        if branch is None:
            branch = self.branch

        exists, _ = self._existing_git_repo()
        if not exists:
            raise errors.MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            self.GIT_HARD_RESET.format(path=self.folder_path, branch=branch).split()
        )

        if p.returncode != 0:
            raise errors.HardResetError(
                "Some error occurred when trying to"
                " execute a hard reset on the repo at"
                " the following path: {}".format(self.folder_path)
            )

    async def update(self) -> (str, str):
        """Update the current branch of this repo.

        Returns
        -------
        `tuple` of `str`
            :py:code`(old commit hash, new commit hash)`

        """
        curr_branch = await self.current_branch()
        old_commit = await self.current_commit(branch=curr_branch)

        await self.hard_reset(branch=curr_branch)

        p = await self._run(self.GIT_PULL.format(path=self.folder_path).split())

        if p.returncode != 0:
            raise errors.UpdateError(
                "Git pull returned a non zero exit code"
                " for the repo located at path: {}".format(self.folder_path)
            )

        new_commit = await self.current_commit(branch=curr_branch)

        self._update_available_modules()
        self._read_info_file()

        return old_commit, new_commit

    async def install_cog(self, cog: Installable, target_dir: Path) -> bool:
        """Install a cog to the target directory.

        Parameters
        ----------
        cog : Installable
            The package to install.
        target_dir : pathlib.Path
            The target directory for the cog installation.

        Returns
        -------
        bool
            The success of the installation.

        """
        if cog not in self.available_cogs:
            raise errors.DownloaderException("That cog does not exist in this repo")

        if not target_dir.is_dir():
            raise ValueError("That target directory is not actually a directory.")

        if not target_dir.exists():
            raise ValueError("That target directory does not exist.")

        return await cog.copy_to(target_dir=target_dir)

    async def install_libraries(
        self, target_dir: Path, libraries: Tuple[Installable] = ()
    ) -> bool:
        """Install shared libraries to the target directory.

        If :code:`libraries` is not specified, all shared libraries in the repo
        will be installed.

        Parameters
        ----------
        target_dir : pathlib.Path
            Directory to install shared libraries to.
        libraries : `tuple` of `Installable`
            A subset of available libraries.

        Returns
        -------
        bool
            The success of the installation.

        """
        if len(libraries) > 0:
            if not all([i in self.available_libraries for i in libraries]):
                raise ValueError("Some given libraries are not available in this repo.")
        else:
            libraries = self.available_libraries

        if len(libraries) > 0:
            ret = True
            for lib in libraries:
                ret = ret and await lib.copy_to(target_dir=target_dir)
            return ret
        return True

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

    async def install_raw_requirements(self, requirements: Tuple[str], target_dir: Path) -> bool:
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
        if len(requirements) == 0:
            return True

        # TODO: Check and see if any of these modules are already available

        p = await self._run(
            self.PIP_INSTALL.format(
                python=executable, target_dir=target_dir, reqs=" ".join(requirements)
            ).split()
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
    def available_cogs(self) -> Tuple[Installable]:
        """`tuple` of `installable` : All available cogs in this Repo.

        This excludes hidden or shared packages.
        """
        # noinspection PyTypeChecker
        return tuple(
            [m for m in self.available_modules if m.type == InstallableType.COG and not m.disabled]
        )

    @property
    def available_libraries(self) -> Tuple[Installable]:
        """`tuple` of `installable` : All available shared libraries in this
        Repo.
        """
        # noinspection PyTypeChecker
        return tuple(
            [m for m in self.available_modules if m.type == InstallableType.SHARED_LIBRARY]
        )

    @classmethod
    async def from_folder(cls, folder: Path):
        repo = cls(name=folder.stem, branch="", url="", folder_path=folder)
        repo.branch = await repo.current_branch()
        repo.url = await repo.current_url()
        repo._update_available_modules()
        return repo


class RepoManager:
    def __init__(self):

        self._repos = {}

        loop = asyncio.get_event_loop()
        loop.create_task(self._load_repos(set=True))  # str_name: Repo

    async def initialize(self):
        await self._load_repos(set=True)

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

    async def add_repo(self, url: str, name: str, branch: str = "master") -> Repo:
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

        # noinspection PyTypeChecker
        r = Repo(url=url, name=name, branch=branch, folder_path=self.repos_folder / name)
        await r.clone()

        self._repos[name] = r

        return r

    def get_repo(self, name: str) -> Union[Repo, None]:
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

    def get_all_repo_names(self) -> Tuple[str]:
        """Get all repo names.

        Returns
        -------
        `tuple` of `str`

        """
        # noinspection PyTypeChecker
        return tuple(self._repos.keys())

    async def delete_repo(self, name: str):
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

        try:
            del self._repos[name]
        except KeyError:
            pass

    async def update_repo(self, repo_name: str) -> MutableMapping[Repo, Tuple[str, str]]:
        repo = self._repos[repo_name]
        old, new = await repo.update()
        return {repo: (old, new)}

    async def update_all_repos(self) -> MutableMapping[Repo, Tuple[str, str]]:
        """Call `Repo.update` on all repositories.

        Returns
        -------
        dict
            A mapping of `Repo` objects that received new commits to a `tuple`
            of `str` containing old and new commit hashes.

        """
        ret = {}
        for repo_name, _ in self._repos.items():
            repo, (old, new) = (await self.update_repo(repo_name)).popitem()
            if old != new:
                ret[repo] = (old, new)
        return ret

    async def _load_repos(self, set=False) -> MutableMapping[str, Repo]:
        ret = {}
        self.repos_folder.mkdir(parents=True, exist_ok=True)
        for folder in self.repos_folder.iterdir():
            if not folder.is_dir():
                continue
            try:
                ret[folder.stem] = await Repo.from_folder(folder)
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

        if set:
            self._repos = ret
        return ret
