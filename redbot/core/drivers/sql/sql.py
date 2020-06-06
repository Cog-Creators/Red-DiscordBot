__all__ = ["SQLDriver"]

import asyncio
import json
import logging
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator, Tuple, Union

from .. import IdentifierData, ConfigCategory
from ...drivers import BaseDriver
from ... import data_manager, errors
from ...utils.dbtools import APSWConnectionWrapper


_locks = defaultdict(asyncio.Lock)

log = logging.getLogger("redbot.sql_driver")


# noinspection PyProtectedMember
class SQLDriver(BaseDriver):
    """
    Subclass of :py:class:`.BaseDriver`.

    .. py:attribute:: file_name

        The name of the file in which to store JSON data.

    .. py:attribute:: data_path

        The path in which to store the file indicated by :py:attr:`file_name`.
    """

    _conn: Optional["APSWConnectionWrapper"] = None
    _data_path: Optional[Path] = None

    def __init__(
        self, cog_name: str, identifier: str, *, data_path_override: Optional[Path] = None,
    ):
        super().__init__(cog_name, identifier)
        self.file_name = f"{identifier}.db"
        if data_path_override is not None:
            data_path = data_path_override
        elif cog_name == "Core" and identifier == "0":
            data_path = data_manager.core_data_path()
        else:
            data_path = data_manager.cog_data_path(raw_name=cog_name)
        data_path.mkdir(parents=True, exist_ok=True)
        self._data_path = data_path / self.file_name

    @property
    def data_path(self) -> Optional[Path]:
        return self._data_path

    @property
    def db(self) -> Optional["APSWConnectionWrapper"]:
        return self._conn

    @db.deleter
    def db(self) -> None:
        if self.db:
            self.db.close()

    @property
    def _lock(self) -> asyncio.Lock:
        return _locks[self.cog_name]

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        # No initializing to do
        if cls._conn is None and cls.data_path is not None:
            if not cls.data_path.exists():
                cls.data_path.touch()
            cls._conn = APSWConnectionWrapper(str(cls.data_path))

    @classmethod
    async def teardown(cls) -> None:
        # No tearing down to do
        del cls.db

    @staticmethod
    def get_config_details() -> Dict[str, Any]:
        # No driver-specific configuration needed
        return {}

    async def get(self, identifier_data: IdentifierData):
        try:
            result = await self._execute(
                "SELECT red_config.get($1)",
                encode_identifier_data(identifier_data),
                method=self._pool.fetchval,
            )
        except asyncpg.UndefinedTableError:
            raise KeyError from None

        if result is None:
            # The result is None both when postgres yields no results, or when it yields a NULL row
            # A 'null' JSON value would be returned as encoded JSON, i.e. the string 'null'
            raise KeyError
        return json.loads(result)

    async def set(self, identifier_data: IdentifierData, value=None):
        try:
            await self._execute(
                "SELECT red_config.set($1, $2::jsonb)",
                encode_identifier_data(identifier_data),
                json.dumps(value),
            )
        except asyncpg.ErrorInAssignmentError:
            raise errors.CannotSetSubfield

    async def clear(self, identifier_data: IdentifierData):
        try:
            await self._execute(
                "SELECT red_config.clear($1)", encode_identifier_data(identifier_data)
            )
        except asyncpg.UndefinedTableError:
            pass

    async def inc(
            self, identifier_data: IdentifierData, value: Union[int, float],
            default: Union[int, float]
    ) -> Union[int, float]:
        try:
            return await self._execute(
                f"SELECT red_config.inc($1, $2, $3)",
                encode_identifier_data(identifier_data),
                value,
                default,
                method=self._pool.fetchval,
            )
        except asyncpg.WrongObjectTypeError as exc:
            raise errors.StoredTypeError(*exc.args)

    async def toggle(self, identifier_data: IdentifierData, default: bool) -> bool:
        try:
            return await self._execute(
                "SELECT red_config.inc($1, $2)",
                encode_identifier_data(identifier_data),
                default,
                method=self._pool.fetchval,
            )
        except asyncpg.WrongObjectTypeError as exc:
            raise errors.StoredTypeError(*exc.args)

    @classmethod
    async def _execute(cls, query: str, *args, method: Optional[Callable] = None) -> Any:
        if method is None:
            method = cls._pool.execute
        log.invisible("Query: %s", query)
        if args:
            log.invisible("Args: %s", args)
        return await method(query, *args)


    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        yield "Core", "0"
        for cog_name in data_manager.cog_data_path().iterdir():
            for cog_id in cog_name.iterdir():
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
                " 1. Drop the entire PostgreSQL database for this instance, or\n"
                " 2. Delete all of Red's data within this database, without dropping the database "
                "itself."
            )
            options = ("1", "2")
            while True:
                resp = input("> ")
                try:
                    drop_db = bool(options.index(resp))
                except ValueError:
                    print("Please type a number corresponding to one of the options.")
                else:
                    break
        if drop_db is True:
            if cls.data_path and cls.data_path.exists():
                cls.data_path.unlink()
        else:
            with DROP_DDL_SCRIPT_PATH.open() as fs:
                await cls._pool.execute(fs.read())

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
            except Exception as err:
                log.critical(f"Error saving: {ident_data.__repr__()}: {data}", exc_info=err)
