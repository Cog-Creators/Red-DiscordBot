from pathlib import Path
from typing import Tuple

from ..json_io import JsonIO

from .red_base import BaseDriver


class JSON(BaseDriver):
    def __init__(self, cog_name, *, data_path_override: Path=None,
                 file_name_override: str="settings.json"):
        super().__init__()
        self.cog_name = cog_name
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

    def get_driver(self):
        return self

    async def get(self, identifiers: Tuple[str]):
        partial = self.data
        for i in identifiers:
            partial = partial[i]
        return partial

    async def set(self, identifiers, value):
        partial = self.data
        for i in identifiers[:-1]:
            if i not in partial:
                partial[i] = {}
            partial = partial[i]

        partial[identifiers[-1]] = value
        await self.jsonIO._threadsafe_save_json(self.data)
