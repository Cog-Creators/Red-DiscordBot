import os
from pathlib import Path
from typing import MutableMapping
from subprocess import run as sp_run

from core import Config
from .errors import InvalidRepoName


class Repo:
    GIT_CLONE = "git clone -b {branch} {url} {folder}"

    def __init__(self, name: str, url: str, branch: str, file_path: Path):
        self.url = url
        self.branch = branch

        self.name = name

        self.file_path = file_path
        self.file_path.mkdir(parents=True, exist_ok=True)

    async def clone(self):
        raise NotImplementedError()

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
            "file_path": self.file_path
        }

    @classmethod
    def from_json(cls, data):
        return Repo(data['name'], data['url'], data['branch'],
                    Path(data['file_path']))


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
                 file_path=self.repos_folder / name)

        r.clone()

        return r
