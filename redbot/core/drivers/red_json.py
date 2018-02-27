from pathlib import Path
from typing import Tuple

from ..json_io import JsonIO

from .red_base import BaseDriver

__all__ = ["JSON"]


class JSON(BaseDriver):
    """
    Subclass of :py:class:`.red_base.BaseDriver`.

    .. py:attribute:: file_name

        The name of the file in which to store JSON data.

    .. py:attribute:: data_path

        The path in which to store the file indicated by :py:attr:`file_name`.
    """
    def __init__(self, cog_name, *, data_path_override: Path=None,
                 file_name_override: str="settings.json"):
        super().__init__(cog_name)
        self.file_name = file_name_override
        if data_path_override:
            self.data_path = data_path_override
        else:
            self.data_path = Path.cwd() / 'cogs' / '.data' / self.cog_name

        self.data_path.mkdir(parents=True, exist_ok=True)

        self.data_path = self.data_path / self.file_name

        self.jsonIO = JsonIO(self.data_path)

        try:
            self.data = self.jsonIO._load_json()
        except FileNotFoundError:
            self.data = {}
            self.jsonIO._save_json(self.data)

    async def get(self, *identifiers: Tuple[str]):
        partial = self.data
        full_identifiers = (self.unique_cog_identifier, *identifiers)
        for i in full_identifiers:
            partial = partial[i]
        return partial

    async def set(self, *identifiers: str, value=None):
        partial = self.data
        full_identifiers = (self.unique_cog_identifier, *identifiers)
        for i in full_identifiers[:-1]:
            if i not in partial:
                partial[i] = {}
            partial = partial[i]

        partial[full_identifiers[-1]] = value
        await self.jsonIO._threadsafe_save_json(self.data)

    async def clear(self, *identifiers: str):
        partial = self.data
        full_identifiers = (self.unique_cog_identifier, *identifiers)
        for i in full_identifiers[:-1]:
            if i not in partial:
                break
            partial = partial[i]
        else:
            del partial[identifiers[-1]]
        await self.jsonIO._threadsafe_save_json(self.data)
