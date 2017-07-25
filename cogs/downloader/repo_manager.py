import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Tuple, MutableMapping
from subprocess import run as sp_run, PIPE
from sys import executable
import pkgutil
import shutil
import functools

from discord.ext import commands

from core import Config
from .errors import *
from .installable import Installable, InstallableType
from .log import log
from .json_mixins import RepoJSONMixin


class Repo(RepoJSONMixin):
    GIT_CLONE = "git clone -b {branch} {url} {folder}"
    GIT_CLONE_NO_BRANCH = "git clone {url} {folder}"
    GIT_CURRENT_BRANCH = "git -C {path} rev-parse --abbrev-ref HEAD"
    GIT_LATEST_COMMIT = "git -C {path} rev-parse {branch}"
    GIT_HARD_RESET = "git -C {path} reset --hard origin/{branch} -q"
    GIT_PULL = "git -C {path} pull -q --ff-only"
    GIT_DIFF_FILE_STATUS = ("git -C {path} diff --no-commit-id --name-status"
                            " {old_hash} {new_hash}")
    GIT_LOG = ("git -C {path} log --relative-date --reverse {old_hash}.."
               " {relative_file_path}")

    PIP_INSTALL = "{python} -m pip install -U -t {target_dir} {reqs}"

    def __init__(self, name: str, url: str, branch: str, folder_path: Path,
                 available_modules: Tuple[Installable]=(), loop: asyncio.AbstractEventLoop=None):
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
        git_path = self.folder_path / '.git'
        return git_path.exists(), git_path

    async def _get_file_update_statuses(
            self, old_hash: str, new_hash: str) -> MutableMapping[str, str]:
        """
        Gets the file update status letters for each changed file between
            the two hashes.
        :param old_hash: Pre-update
        :param new_hash: Post-update
        :return: Mapping of filename -> status_letter
        """
        p = await self._run(
            self.GIT_DIFF_FILE_STATUS.format(
                path=self.folder_path,
                old_hash=old_hash,
                new_hash=new_hash
            )
        )

        if p.returncode != 0:
            raise GitDiffError("Git diff failed for repo at path:"
                               " {}".format(self.folder_path))

        stdout = p.stdout.strip().decode().split('\n')

        ret = {}

        for filename in stdout:
            # TODO: filter these filenames by ones in self.available_modules
            status, _, filepath = filename.partition('\t')
            ret[filepath] = status

        return ret

    async def _get_commit_notes(self, old_commit_hash: str,
                                relative_file_path: str) -> str:
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
                relative_file_path=relative_file_path
            )
        )

        if p.returncode != 0:
            raise GitException("An exception occurred while executing git log on"
                               " this repo: {}".format(self.folder_path))

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
        for file_finder, name, is_pkg in pkgutil.walk_packages(path=[str(self.folder_path), ]):
            curr_modules.append(
                Installable(location=self.folder_path / name)
            )
        self.available_modules = curr_modules

        # noinspection PyTypeChecker
        return tuple(self.available_modules)

    async def _run(self, *args, **kwargs):
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        kwargs['env'] = env
        async with self._repo_lock:
            return await self._loop.run_in_executor(
                self._executor,
                functools.partial(sp_run, *args, stdout=PIPE, **kwargs)
            )

    async def clone(self) -> Tuple[str]:
        """
        Clones a new repo.
        :return: List of available modules from this repo.
        """
        exists, path = self._existing_git_repo()
        if exists:
            raise ExistingGitRepo(
                "A git repo already exists at path: {}".format(path)
            )

        if self.branch is not None:
            p = await self._run(
                self.GIT_CLONE.format(
                    branch=self.branch,
                    url=self.url,
                    folder=self.folder_path
                ).split()
            )
        else:
            p = await self._run(
                self.GIT_CLONE_NO_BRANCH.format(
                    url=self.url,
                    folder=self.folder_path
                ).split()
            )

        if p.returncode != 0:
            raise CloningError("Error when running git clone.")

        if self.branch is None:
            self.branch = await self.current_branch()

        self._read_info_file()

        return self._update_available_modules()

    async def current_branch(self) -> str:
        """
        Determines the current branch using git commands.
        :return: Current branch name
        """
        exists, _ = self._existing_git_repo()
        if not exists:
            raise MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            self.GIT_CURRENT_BRANCH.format(
                path=self.folder_path
            ).split()
        )

        if p.returncode != 0:
            raise GitException("Could not determine current branch"
                               " at path: {}".format(self.folder_path))

        return p.stdout.decode().strip()

    async def current_commit(self, branch: str=None) -> str:
        """
        Determines the current commit hash of the repo.
        :param branch: Override for repo's branch attribute
        :return: Commit hash string
        """
        if branch is None:
            branch = self.branch

        exists, _ = self._existing_git_repo()
        if not exists:
            raise MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            self.GIT_LATEST_COMMIT.format(
                path=self.folder_path,
                branch=branch
            ).split()
        )

        if p.returncode != 0:
            raise CurrentHashError("Unable to determine old commit hash.")

        return p.stdout.decode().strip()

    async def hard_reset(self, branch: str=None) -> None:
        """
        Performs a hard reset on the current repo.
        :param branch: Override for repo branch attribute.
        :return:
        """
        if branch is None:
            branch = self.branch

        exists, _ = self._existing_git_repo()
        if not exists:
            raise MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            self.GIT_HARD_RESET.format(
                path=self.folder_path,
                branch=branch
            ).split()
        )

        if p.returncode != 0:
            raise HardResetError("Some error occurred when trying to"
                                 " execute a hard reset on the repo at"
                                 " the following path: {}".format(self.folder_path))

    async def update(self) -> (str, str):
        """
        Updates the current branch of this repo.
        :return: Old commit hash
        :return: New commit hash
        """
        curr_branch = await self.current_branch()
        old_commit = await self.current_commit(branch=curr_branch)

        await self.hard_reset(branch=curr_branch)

        p = await self._run(
            self.GIT_PULL.format(
                path=self.folder_path
            ).split()
        )

        if p.returncode != 0:
            raise UpdateError("Git pull returned a non zero exit code"
                              " for the repo located at path: {}".format(self.folder_path))

        new_commit = await self.current_commit(branch=curr_branch)

        self._update_available_modules()
        self._read_info_file()

        return old_commit, new_commit

    async def install_cog(self, cog: Installable, target_dir: Path) -> bool:
        """
        Copies a cog to the target directory.
        :param cog:
        :param target_dir:
        :return: bool - if installation succeeded
        """
        if cog not in self.available_cogs:
            raise DownloaderException("That cog does not exist in this repo")

        if not target_dir.is_dir():
            raise ValueError("That target directory is not actually a directory.")

        if not target_dir.exists():
            raise ValueError("That target directory does not exist.")

        return await cog.copy_to(target_dir=target_dir)

    async def install_libraries(self, target_dir: Path, libraries: Tuple[Installable]=()) -> bool:
        """
        Copies all shared libraries (or a given subset) to the target
            directory.
        :param target_dir:
        :param libraries: A subset of available libraries
        :return: bool - all copies succeeded
        """
        if libraries:
            if not all([i in self.available_libraries for i in libraries]):
                raise ValueError("Some given libraries are not available in this repo.")
        else:
            libraries = self.available_libraries

        if libraries:
            return all([lib.copy_to(target_dir=target_dir) for lib in libraries])
        return True

    async def install_requirements(self, cog: Installable, target_dir: Path) -> bool:
        """
        Installs the requirements defined by the requirements
            attribute on the cog object and puts them in the given
            target directory.
        :param cog:
        :param target_dir:
        :return:
        """
        if not target_dir.is_dir():
            raise ValueError("Target directory is not a directory.")
        target_dir.mkdir(parents=True, exist_ok=True)

        return await self.install_raw_requirements(cog.requirements, target_dir)

    async def install_raw_requirements(self, requirements: Tuple[str], target_dir: Path) -> bool:
        """
        Installs a list of requirements using pip and places them into
            the given target directory.
        :param requirements:
        :param target_dir:
        :return:
        """
        if len(requirements) == 0:
            return True

        # TODO: Check and see if any of these modules are already available

        p = await self._run(
            self.PIP_INSTALL.format(
                python=executable,
                target_dir=target_dir,
                reqs=" ".join(requirements)
            ).split()
        )

        if p.returncode != 0:
            log.error("Something went wrong when installing"
                      " the following requirements:"
                      " {}".format(", ".join(requirements)))
            return False
        return True

    @property
    def available_cogs(self) -> Tuple[Installable]:
        """
        Returns a list of available cogs (not shared libraries and not hidden).
        :return: tuple(installable)
        """
        # noinspection PyTypeChecker
        return tuple(
            [m for m in self.available_modules
             if m.type == InstallableType.COG and not m.hidden]
        )

    @property
    def available_libraries(self) -> Tuple[Installable]:
        """
        Returns a list of available shared libraries in this repo.
        """
        # noinspection PyTypeChecker
        return tuple(
            [m for m in self.available_modules
             if m.type == InstallableType.SHARED_LIBRARY]
        )

    def to_json(self):
        return {
            "url": self.url,
            "name": self.name,
            "branch": self.branch,
            "folder_path": self.folder_path.relative_to(Path.cwd()).parts,
            "available_modules": [m.to_json() for m in self.available_modules]
        }

    @classmethod
    def from_json(cls, data):
        # noinspection PyTypeChecker
        return Repo(data['name'], data['url'], data['branch'],
                    Path.cwd() / Path(*data['folder_path']),
                    tuple([Installable.from_json(m) for m in data['available_modules']]))


class RepoManager:
    def __init__(self, downloader_config: Config):
        self.downloader_config = downloader_config

        self.repos_folder = Path(__file__).parent / 'repos'

        self._repos = self._load_repos()  # str_name: Repo

    def does_repo_exist(self, name: str) -> bool:
        return name in self._repos

    @staticmethod
    def validate_and_normalize_repo_name(name: str) -> str:
        if not name.isidentifier():
            raise InvalidRepoName("Not a valid Python variable name.")
        return name.lower()

    async def add_repo(self, url: str, name: str, branch: str="master") -> Repo:
        """
        Adds a repo and clones it.
        :param url:
        :param name:
        :param branch:
        :return:
        """
        name = self.validate_and_normalize_repo_name(name)
        if self.does_repo_exist(name):
            raise InvalidRepoName(
                "That repo name you provided already exists."
                " Please choose another."
            )

        # noinspection PyTypeChecker
        r = Repo(url=url, name=name, branch=branch,
                 folder_path=self.repos_folder / name)
        await r.clone()

        self._repos[name] = r
        await self._save_repos()

        return r

    def get_repo(self, name: str) -> Repo:
        """
        Returns a repo object with the given name.
        :param name: Repo name
        :return: Repo object or None
        """
        return self._repos.get(name, None)

    def get_all_repo_names(self) -> Tuple[str]:
        """
        Returns a tuple of all repo names
        :return:
        """
        # noinspection PyTypeChecker
        return tuple(self._repos.keys())

    async def delete_repo(self, name: str):
        """
        Deletes a repo and its' folders with the given name.
        :param name:
        :return:
        """
        repo = self.get_repo(name)
        if repo is None:
            raise MissingGitRepo("There is no repo with the name {}".format(name))

        shutil.rmtree(str(repo.folder_path))

        repos = self.downloader_config.repos()
        try:
            del self._repos[name]
        except KeyError:
            pass

        await self._save_repos()

    async def update_all_repos(self) -> MutableMapping[Repo, Tuple[str, str]]:
        """
        Calls repo.update() on all repos, returns a mapping of repos
            that received new commits to a tuple containing old and
            new commit hashes.
        :return:
        """
        ret = {}
        for _, repo in self._repos.items():
            old, new = await repo.update()
            if old != new:
                ret[repo] = (old, new)

        await self._save_repos()
        return ret

    def _load_repos(self) -> MutableMapping[str, Repo]:
        return {
            name: Repo.from_json(data) for name, data in
            self.downloader_config.repos().items()
        }

    async def _save_repos(self):
        repo_json_info = {name: r.to_json() for name, r in self._repos.items()}
        await self.downloader_config.repos.set(repo_json_info)
