import os
from pathlib import Path
from typing import MutableMapping, List
from subprocess import run as sp_run
import importlib.util

from core import Config
from .errors import InvalidRepoName, ExistingGitRepo, CloningError


class Repo:
    GIT_CLONE = "git clone -b {branch} {url} {folder}"

    def __init__(self, name: str, url: str, branch: str, folder_path: Path,
                 available_modules: List[str]=()):
        self.url = url
        self.branch = branch

        self.name = name

        self.folder_path = folder_path
        self.folder_path.mkdir(parents=True, exist_ok=True)

        self.available_modules = available_modules

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

        p = self._run(
            self.GIT_CLONE.format(
                branch=self.branch,
                url=self.url,
                folder=self.folder_path
            )
        )

        if p.returncode() != 0:
            raise CloningError("Error when running git clone.")

        return self._update_available_modules()

    async def update(self):
        raise NotImplementedError()

    def _run(*args, **kwargs):
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'
        kwargs['env'] = env
        return sp_run(*args, **kwargs)

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

        self.repos_folder = Path(self.__file__).parent / 'repos'

        self.repos = MutableMapping[str, Repo]

    def does_repo_exist(self, name: str) -> bool:
        return name in self.repos

    @staticmethod
    def normalize_repo_name(name: str) -> str:
        ret = name.replace(" ", "_")
        return ret.lower()

    async def add_repo(self, url: str, name: str, branch: str="master") -> Repo:
        name = self.normalize_repo_name(name)
        if name in self.repos:
            raise InvalidRepoName(
                "That repo name you provided already exists."
                " Please choose another."
            )

        # noinspection PyTypeChecker
        r = Repo(url=url, name=name, branch=branch,
                 folder_path=self.repos_folder / name)

        r.clone()

        return r
