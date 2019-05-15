import copy
import json
import weakref
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, AsyncIterator, Optional

from redbot.core import data_manager
from .. import errors
from ..json_io import JsonIO

from .base import BaseDriver, IdentifierData, ConfigCategory

__all__ = ["JsonDriver"]


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


# noinspection PyProtectedMember
class JsonDriver(BaseDriver):
    """
    Subclass of :py:class:`.BaseDriver`.

    .. py:attribute:: file_name

        The name of the file in which to store JSON data.

    .. py:attribute:: data_path

        The path in which to store the file indicated by :py:attr:`file_name`.
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
        if data_path_override is not None:
            self.data_path = data_path_override
        elif cog_name == "Core" and identifier == "0":
            self.data_path = data_manager.core_data_path()
        else:
            self.data_path = data_manager.cog_data_path(raw_name=cog_name)
        self.jsonIO = JsonIO(self.data_path / self.file_name)

        self.data_path.mkdir(parents=True, exist_ok=True)
        self._load_data()

    @property
    def data(self):
        return _shared_datastore.get(self.cog_name)

    @data.setter
    def data(self, value):
        _shared_datastore[self.cog_name] = value

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        # No initializing to do
        return

    @classmethod
    async def teardown(cls) -> None:
        # No tearing down to do
        return

    @staticmethod
    def get_config_details() -> Dict[str, Any]:
        # No driver-specific configuration needed
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

    def migrate_identifier(self, raw_identifier: int):
        if self.unique_cog_identifier in self.data:
            # Data has already been migrated
            return
        poss_identifiers = [str(raw_identifier), str(hash(raw_identifier))]
        for ident in poss_identifiers:
            if ident in self.data:
                self.data[self.unique_cog_identifier] = self.data[ident]
                del self.data[ident]
                self.jsonIO._save_json(self.data)
                break

    async def get(self, identifier_data: IdentifierData):
        partial = self.data
        full_identifiers = identifier_data.to_tuple()
        for i in full_identifiers:
            partial = partial[i]
        return copy.deepcopy(partial)

    async def set(self, identifier_data: IdentifierData, value=None):
        partial = self.data
        full_identifiers = identifier_data.to_tuple()
        for i in full_identifiers[:-1]:
            try:
                partial = partial.setdefault(i, {})
            except AttributeError:
                # Tried to set sub-field of non-object
                raise errors.CannotSetSubfield

        partial[full_identifiers[-1]] = copy.deepcopy(value)
        await self.jsonIO._threadsafe_save_json(self.data)

    async def clear(self, identifier_data: IdentifierData):
        partial = self.data
        full_identifiers = identifier_data.to_tuple()
        try:
            for i in full_identifiers[:-1]:
                partial = partial[i]
            del partial[full_identifiers[-1]]
        except KeyError:
            pass
        else:
            await self.jsonIO._threadsafe_save_json(self.data)

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        yield "Core", "0"
        for _dir in data_manager.cog_data_path().iterdir():
            fpath = _dir / "settings.json"
            if not fpath.exists():
                continue
            with fpath.open() as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    continue
            if not isinstance(data, dict):
                continue
            for cog, inner in data.items():
                if not isinstance(inner, dict):
                    continue
                for cog_id in inner:
                    yield cog, cog_id

    async def import_data(self, cog_data, custom_group_data):
        def update_write_data(identifier_data: IdentifierData, _data):
            partial = self.data
            idents = identifier_data.to_tuple()
            for ident in idents[:-1]:
                partial = partial.setdefault(ident, {})
            partial[idents[-1]] = _data

        for category, all_data in cog_data:
            splitted_pkey = self._split_primary_key(category, custom_group_data, all_data)
            for pkey, data in splitted_pkey:
                ident_data = IdentifierData(
                    self.unique_cog_identifier,
                    category,
                    pkey,
                    (),
                    *ConfigCategory.get_pkey_info(category, custom_group_data)
                )
                update_write_data(ident_data, data)
        await self.jsonIO._threadsafe_save_json(self.data)
