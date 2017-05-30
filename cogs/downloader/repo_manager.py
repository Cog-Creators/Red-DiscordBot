import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Tuple, MutableMapping
from subprocess import run as sp_run, PIPE
import importlib.util

import functools

from core import Config
from .errors import *


class Repo:
    GIT_CLONE = "git clone -b {branch} {url} {folder}"
    GIT_CURRENT_BRANCH = "git -C {path} rev-parse --abbrev-ref HEAD"
    GIT_LATEST_COMMIT = "git -C {path} rev-parse {branch}"
    GIT_HARD_RESET = "git -C {path} reset --hard origin/{branch} -q"
    GIT_PULL = "git -C {path} pull -q --ff-only"
    GIT_DIFF_FILE_STATUS = ("git -C {path} diff --no-commit-id --name-status"
                            " {old_hash} {new_hash}")
    GIT_LOG = ("git -C {path} log --relative-date --reverse {old_hash}.."
               " {relative_file_path}")

    def __init__(self, name: str, url: str, branch: str, folder_path: Path,
                 available_modules: Tuple[str]=(), loop: asyncio.AbstractEventLoop=None):
        self.url = url
        self.branch = branch

        self.name = name

        self.folder_path = folder_path
        self.folder_path.mkdir(parents=True, exist_ok=True)

        self.available_modules = available_modules

        self._executor = ThreadPoolExecutor(1)

        self._repo_lock = asyncio.Lock()

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

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
        :param file_relative_path: Path relative to the repo folder of the file
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
        for name in self.folder_path.iterdir():
            if name.is_dir():
                spec = importlib.util.spec_from_file_location(
                    name, location=str(self.folder_path / name)
                )
                if spec is not None:
                    curr_modules.append(name)
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

        p = await self._run(
            self.GIT_CLONE.format(
                branch=self.branch,
                url=self.url,
                folder=self.folder_path
            ).split()
        )

        if p.returncode != 0:
            raise CloningError("Error when running git clone.")

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
            )
        )

        if p.returncode != 0:
            raise UpdateError("Git pull returned a non zero exit code"
                              " for the repo located at path: {}".format(self.folder_path))

        new_commit = await self.current_commit(branch=curr_branch)

        self._update_available_modules()

        return old_commit, new_commit

    def to_json(self):
        return {
            "url": self.url,
            "name": self.name,
            "branch": self.branch,
            "folder_path": self.folder_path,
            "available_modules": self.available_modules
        }

    @classmethod
    def from_json(cls, data):
        return Repo(data['name'], data['url'], data['branch'],
                    Path(data['folder_path']),
                    data['available_modules'])


class RepoManager:
    def __init__(self, downloader_config: Config):
        self.downloader_config = downloader_config

        self.repos_folder = Path(__file__).parent / 'repos'

        self.repos = self._load_repos()  # str_name: Repo

    def does_repo_exist(self, name: str) -> bool:
        return name in self.repos

    @staticmethod
    def normalize_repo_name(name: str) -> str:
        ret = name.replace(" ", "_")
        return ret.lower()

    async def add_repo(self, url: str, name: str, branch: str="master") -> Repo:
        name = self.normalize_repo_name(name)
        if self.does_repo_exist(name):
            raise InvalidRepoName(
                "That repo name you provided already exists."
                " Please choose another."
            )

        # noinspection PyTypeChecker
        r = Repo(url=url, name=name, branch=branch,
                 folder_path=self.repos_folder / name)
        await r.clone()

        self.repos[name] = r
        await self._save_repos()

        return r

    async def get_repo(self, name: str):
        """
        Returns a repo object with the given name.
        :param name: Repo name
        :return: Repo object or None
        """
        return self.repos.get(name, None)

    async def update_all_repos(self) -> MutableMapping[Repo, Tuple[str, str]]:
        ret = {}
        for _, repo in self.repos.items():
            ret[repo] = await repo.update()

        await self._save_repos()
        return ret

    def _load_repos(self) -> MutableMapping[str, Repo]:
        return {
            name: Repo.from_json(data) for name, data in
            self.downloader_config.repos().items()
        }

    async def _save_repos(self):
        repo_json_info = {name: r.to_json() for name, r in self.repos}
        await self.downloader_config.set("repos", repo_json_info)
