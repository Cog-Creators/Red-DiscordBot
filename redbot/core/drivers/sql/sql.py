import asyncio
import concurrent
from collections import defaultdict
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator, Tuple

from .queries import (
    _create_table,
    _get_query,
    _set_query,
    _clear_query,
    _prep_query,
    _get_type_query,
)
from .. import IdentifierData, ConfigCategory
from ..log import log
from ... import data_manager
from ...drivers import BaseDriver
from ...utils.dbtools import APSWConnectionWrapper

try:
    import ujson as json
except ImportError:
    import json

_locks = defaultdict(asyncio.Lock)

__all__ = ["SQLDriver"]


# noinspection PyProtectedMember
class SQLDriver(BaseDriver):
    """
    Subclass of :py:class:`.BaseDriver`.

    .. py:attribute:: file_name

        The name of the file in which to store JSON data.

    .. py:attribute:: data_path

        The path in which to store the file indicated by :py:attr:`file_name`.
    """

    db: Optional["APSWConnectionWrapper"] = None
    data_path: Optional[Path] = None

    def __init__(
        self, cog_name: str, identifier: str, *, data_path_override: Optional[Path] = None,
    ):
        super().__init__(cog_name, identifier)
        self.file_name = f"{identifier}.rdb"
        if data_path_override is not None:
            data_path = data_path_override
        elif cog_name == "Core" and identifier == "0":
            data_path = data_manager.core_data_path()
        else:
            data_path = data_manager.cog_data_path(raw_name=cog_name)
        data_path.mkdir(parents=True, exist_ok=True)
        self.data_path = data_path / self.file_name
        if not self.data_path.exists():
            self.data_path.touch()
        self.db = APSWConnectionWrapper(str(self.data_path))

    @property
    def _lock(self) -> asyncio.Lock:
        return _locks[self.cog_name]

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        # No initializing to do
        return

    @classmethod
    async def teardown(cls) -> None:
        # No tearing down to do
        if cls.db is not None:
            cls.db.close()

    @staticmethod
    def get_config_details() -> Dict[str, Any]:
        # No driver-specific configuration needed
        return {}

    async def get(self, identifier_data: IdentifierData):
        _full_identifiers = identifier_data.to_tuple()
        cog_name, uuid, category, full_identifiers = (
            _full_identifiers[0],
            _full_identifiers[1],
            _full_identifiers[2],
            _full_identifiers[3:],
        )
        identifier_string = "$"
        if full_identifiers:
            identifier_string += "." + ".".join(full_identifiers)
        query = _get_query.format(table_name=category)
        type_query = _get_type_query.format(table_name=category)
        result = await self._execute(query, category, type_query, path=identifier_string)
        return result

    async def set(self, identifier_data: IdentifierData, value=None):
        try:
            _full_identifiers = identifier_data.to_tuple()
            cog_name, uuid, category, full_identifiers = (
                _full_identifiers[0],
                _full_identifiers[1],
                _full_identifiers[2],
                _full_identifiers[3:],
            )
            identifier_string = "$"
            if full_identifiers:
                identifier_string += "." + ".".join(full_identifiers)
            value = json.dumps(value)

            query = _set_query.format(table_name=category)
            async with self._lock:
                await self._execute(query, category, path=identifier_string, data=value)
        except Exception as exc:
            log.error(
                f"{exc} when saving data for '{self.cog_name}' "
                f"id:{self.unique_cog_identifier} "
                f"|| {value}"
            )
            raise

    async def clear(self, identifier_data: IdentifierData):
        _full_identifiers = identifier_data.to_tuple()
        cog_name, uuid, category, full_identifiers = (
            _full_identifiers[0:1],
            _full_identifiers[1:2],
            _full_identifiers[2:3],
            _full_identifiers[3:],
        )
        if cog_name:
            (cog_name,) = cog_name
        if uuid:
            (uuid,) = uuid
        if category:
            (category,) = category

        identifier_string = "$"
        if full_identifiers:
            identifier_string += "." + ".".join(full_identifiers)
        if not category:
            async with self._lock:  # Changing the generic schema ... is painful...
                self.db.close()
                self.data_path.unlink()
                self.db = APSWConnectionWrapper(str(self.data_path))
            return
        else:
            query = _clear_query.format(table_name=category)
        async with self._lock:
            await self._execute(query, category, path=identifier_string)

    async def _execute(
        self,
        query: str,
        category: str,
        type_query: Optional[str] = None,
        path: Optional[str] = None,
        data: Optional[str] = ...,
    ) -> Any:
        log.invisible("Query: %s", query)
        if category:
            self.db.cursor().execute(_create_table.format(table_name=category))
            self.db.cursor().execute(_prep_query.format(table_name=category))
        if type_query:
            obj_type = self.db.cursor().execute(type_query, (path,))
            obj_type = obj_type.fetchone()
            obj_type = obj_type[0]
            if obj_type is None:
                raise KeyError
        else:
            obj_type = ...
        _data = {
            "path": path,
        }
        if data is not ...:
            _data.update({"value": data})
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.db.cursor().execute, query, _data)]
            ):
                output = future.result()
                output = output.fetchone()
                if obj_type is ...:
                    return
                output = output[0]
                if obj_type in ["true", "false"] and isinstance(output, int):
                    output = bool(output)
                elif obj_type not in ["text"] and isinstance(output, str):
                    output = json.loads(output)

        return output

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        yield "Core", "0"
        for cog_name in data_manager.cog_data_path().iterdir():
            for cog_id in cog_name.iterdir():
                if cog_id.suffix in {".rdb"}:
                    yield cog_name.stem, cog_id.stem

    @classmethod
    async def delete_all_data(
        cls, *, interactive: bool = False, drop_db: Optional[bool] = None, **kwargs
    ) -> None:
        """Delete all data being stored by this driver.

        Parameters
        ----------
        interactive : bool
            Set to ``True`` to allow the method to ask the user for
            input from the console, regarding the other unset parameters
            for this method.
        drop_db : Optional[bool]
            Set to ``True`` to drop the entire database for the current
            bot's instance. Otherwise, schemas within the database which
            store bot data will be dropped, as well as functions,
            aggregates, event triggers, and meta-tables.

        """
        if interactive is True and drop_db is None:
            print(
                "Please choose from one of the following options:\n"
                "0. Keeps Reds data saved in the existing databases"
                " 1. Delete all of Red's data."
            )
            options = ("0", "1")
            while True:
                resp = input("> ")
                try:
                    drop_db = bool(options.index(resp))
                except ValueError:
                    print("Please type a number corresponding to one of the options.")
                else:
                    break
        if drop_db:
            for cog_name in data_manager.cog_data_path().iterdir():
                for cog_id in cog_name.iterdir():
                    if cog_id.suffix in {".rdb"}:
                        cog_id.unlink()

    async def import_data(self, cog_data, custom_group_data):
        log.info(f"Converting Cog: {self.cog_name}")
        for category, all_data in cog_data:
            log.info(f"Converting cog category: {category}")
            ident_data = IdentifierData(
                self.cog_name,
                self.unique_cog_identifier,
                category,
                (),
                (),
                *ConfigCategory.get_pkey_info(category, custom_group_data),
            )
            try:
                await self.set(ident_data, all_data)
            except Exception:
                await self._individual_migrate(category, custom_group_data, all_data)

    async def _individual_migrate(self, category, custom_group_data, all_data):
        splitted_pkey = self._split_primary_key(category, custom_group_data, all_data)
        for pkey, data in splitted_pkey:
            ident_data = IdentifierData(
                self.cog_name,
                self.unique_cog_identifier,
                category,
                pkey,
                (),
                *ConfigCategory.get_pkey_info(category, custom_group_data),
            )
            try:
                await self.set(ident_data, data)
            except Exception as exc:
                log.critical(f"{exc} when saving: {ident_data.__repr__()}: {data}")
