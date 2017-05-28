from pathlib import Path
from typing import MutableMapping

from core import Config
from .errors import InvalidRepoName


class Repo:
    def __init__(self, url: str, name: str):
        self.url = url

        self.name = name

        self.filepath = Path()

    async def clone(self):
        raise NotImplementedError()

    async def update(self):
        raise NotImplementedError()

    def to_json(self):
        return {
            "url": self.url,
            "name": self.name
        }

    @classmethod
    def from_json(cls, data):
        return Repo(data['url'], data['name'])


class RepoManager:
    def __init__(self, downloader_config: Config):
        self.downloader_config = downloader_config

        self.repos_folder = Path(self.__file__).parent / 'repos'

        self.repos = MutableMapping[str, Repo]

    async def add_repo(self, url: str, name: str):
        if name.lower() in self.repos:
            raise InvalidRepoName(
                "That repo name you provided already exists."
                " Please choose another."
            )
