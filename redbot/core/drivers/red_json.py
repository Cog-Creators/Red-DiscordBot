from pathlib import Path
from typing import Tuple, Optional
import copy
import weakref
import logging

from ..json_io import JsonIO

from .red_base import BaseDriver

__all__ = ["JSON"]


_shared_datastore = {}
_driver_counts = {}
_finalizers = []

log = logging.getLogger("redbot.json_driver")


def finalize_driver(cog_name):
    if cog_name not in _driver_counts:
        return

    _driver_counts[cog_name] -= 1

    if _driver_counts[cog_name] == 0:
        if cog_name in _shared_datastore:
            del _shared_datastore[cog_name]

    for f in _finalizers:
        if not f.alive:
            _finalizers.remove(f)


class JSON(BaseDriver):
    """JSON driver implementation.

    This backend is the easiest to set up, and suitable for most small
    bots, however one should consider switching to a database backend
    should their config files start to significantly grow in size
    (e.g. if a single JSON grows larger than multiple MB), or the
    access frequency greatly increases.

    Parameters
    ----------
    cog_name : str
        The name of the cog class. This will be the same as the name
        of the folder containing the JSON file.
    identifier : str
        A unique identifier which will be the first key in the JSON
        dict, to avoid any possible naming conflicts with other cogs.
    data_path_override : Optional[pathlib.Path]
        Where the JSON file will be saved.
    file_name_override : str
        The name of the JSON file, including the extension. defaults
        to _settings.json_.

    Attributes
    ----------
    file_name : str
        The name of the file in which to store JSON data.
    data_path : pathlib.Path
        The path in which to store the file indicated by `file_name`.

    """

    def __init__(
        self,
        cog_name: str,
        identifier: str,
        *,
        data_path_override: Optional[Path] = None,
        file_name_override: str = "settings.json"
    ):
        super().__init__(cog_name, identifier)
        self.file_name = file_name_override
        if data_path_override:
            self.data_path = data_path_override
        else:
            self.data_path = Path.cwd() / "cogs" / ".data" / self.cog_name

        self.data_path.mkdir(parents=True, exist_ok=True)

        self.data_path = self.data_path / self.file_name

        self.jsonIO = JsonIO(self.data_path)

        self._load_data()

    @property
    def data(self):
        return _shared_datastore.get(self.cog_name)

    @data.setter
    def data(self, value):
        _shared_datastore[self.cog_name] = value

    @staticmethod
    def get_config_details() -> dict:
        return {}

    def _load_data(self):
        if self.cog_name not in _driver_counts:
            _driver_counts[self.cog_name] = 0
        _driver_counts[self.cog_name] += 1

        _finalizers.append(weakref.finalize(self, finalize_driver, self.cog_name))

        if self.data is not None:
            return

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
        return copy.deepcopy(partial)

    async def set(self, *identifiers: str, value=None):
        partial = self.data
        full_identifiers = (self.unique_cog_identifier, *identifiers)
        for i in full_identifiers[:-1]:
            if i not in partial:
                partial[i] = {}
            partial = partial[i]

        partial[full_identifiers[-1]] = copy.deepcopy(value)
        await self.jsonIO._threadsafe_save_json(self.data)

    async def clear(self, *identifiers: str):
        partial = self.data
        full_identifiers = (self.unique_cog_identifier, *identifiers)
        try:
            for i in full_identifiers[:-1]:
                partial = partial[i]
            del partial[full_identifiers[-1]]
        except KeyError:
            pass
        else:
            await self.jsonIO._threadsafe_save_json(self.data)
