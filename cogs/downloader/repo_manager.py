import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List
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

    def __init__(self, name: str, url: str, branch: str, folder_path: Path,
                 available_modules: List[str]=(), loop: asyncio.AbstractEventLoop=None):
        self.url = url
        self.branch = branch

        self.name = name

        self.folder_path = folder_path
        self.folder_path.mkdir(parents=True, exist_ok=True)

        self.available_modules = available_modules

        self._executor = ThreadPoolExecutor(4)

        self._loop = loop
        if self._loop is None:
            self._loop = asyncio.get_event_loop()

    def _existing_git_repo(self) -> (bool, Path):
        git_path = self.folder_path / '.git'
        return git_path.exists(), git_path

    def _update_available_modules(self) -> List[str]:
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
        return self.available_modules

    async def clone(self) -> List[str]:
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

    async def current_commit(self) -> str:
        """
        Determines the current commit hash of the repo.
        :return: Commit hash string
        """
        exists, _ = self._existing_git_repo()
        if not exists:
            raise MissingGitRepo(
                "A git repo does not exist at path: {}".format(self.folder_path)
            )

        p = await self._run(
            self.GIT_LATEST_COMMIT.format(
                path=self.folder_path,
                branch=self.branch
            ).split()
        )

        if p.returncode != 0:
            raise CurrentHashError("Unable to determine old commit hash.")

        return p.stdout.decode().strip()

    async def hard_reset(self):
        """
        Performs a hard reset on the current repo.
        :return:
        """
        raise NotImplementedError()

    async def update(self):
        raise NotImplementedError()

    async def _run(self, *args, **kwargs):
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        kwargs['env'] = env
        return await self._loop.run_in_executor(
            self._executor,
            functools.partial(sp_run, *args, stdout=PIPE, **kwargs)
        )

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

        self.repos = {}  # str_name: Repo

    def does_repo_exist(self, name: str) -> bool:
        return name in self.repos

    @staticmethod
    def normalize_repo_name(name: str) -> str:
        ret = name.replace(" ", "_")
        return ret.lower()

    async def add_repo(self, url: str, name: str, branch: str="master") -> Repo:
        name = self.normalize_repo_name(name)
        if name in self.repos.keys():
            raise InvalidRepoName(
                "That repo name you provided already exists."
                " Please choose another."
            )

        # noinspection PyTypeChecker
        r = Repo(url=url, name=name, branch=branch,
                 folder_path=self.repos_folder / name)

        await r.clone()

        return r
