import getpass
import json
from pathlib import Path
from typing import Optional, Any, AsyncIterator, Tuple, Union, Callable, List

try:
    import asyncpg
except ModuleNotFoundError:
    asyncpg = None

from ... import data_manager, errors
from ..base import BaseDriver, IdentifierData, ConfigCategory
from ..log import log

__all__ = ["PostgresDriver"]

_PKG_PATH = Path(__file__).parent
DDL_SCRIPT_PATH = _PKG_PATH / "ddl.sql"
DROP_DDL_SCRIPT_PATH = _PKG_PATH / "drop_ddl.sql"


class PostgresDriver(BaseDriver):

    _pool: Optional["asyncpg.pool.Pool"] = None

    @classmethod
    async def initialize(cls, **storage_details) -> None:
        if asyncpg is None:
            raise errors.MissingExtraRequirements(
                "Red must be installed with the [postgres] extra to use the PostgreSQL driver"
            )
        cls._pool = await asyncpg.create_pool(**storage_details)
        with DDL_SCRIPT_PATH.open() as fs:
            await cls._pool.execute(fs.read())

    @classmethod
    async def teardown(cls) -> None:
        if cls._pool is not None:
            await cls._pool.close()

    @staticmethod
    def get_config_details():
        host = input("Enter PostgreSQL server address [localhost]: ")
        if not host:
            host = "localhost"
        while True:
            port = input("Enter PostgreSQL server port [5432]: ")
            if not port:
                port = 5432
                break
            else:
                try:
                    port = int(port)
                except ValueError:
                    print("Port must be a number")
                else:
                    break
        user = input("Enter PostgreSQL server username [postgres]: ")
        if not user:
            user = "postgres"

        password = getpass.getpass("Enter PostgreSQL server password (input will be hidden): ")

        database = input("Enter PostgreSQL database name [postgres]: ")
        if not database:
            database = "postgres"

        return {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
        }

    async def get(self, identifier_data: IdentifierData):
        pkeys, pkey_type, pkey_len = self._get_pkey_info(identifier_data)
        try:
            result = await self._execute(
                f"""
                SELECT config.get(
                  cog_name := $1,
                  cog_id := $2,
                  config_category := $3,
                  pkey_len := $4,
                  pkeys := $5::{pkey_type}[],
                  identifiers := $6
                )
                """,
                self.cog_name,
                self.unique_cog_identifier,
                identifier_data.category,
                pkey_len,
                pkeys,
                list(identifier_data.identifiers),
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
        pkeys, pkey_type, pkey_len = self._get_pkey_info(identifier_data)
        try:
            await self._execute(
                f"""
                SELECT config.set(
                  cog_name := $1,
                  cog_id := $2,
                  config_category := $3,
                  new_value := $4,
                  pkey_len := $5,
                  pkey_type := $6,
                  pkeys := $7::{pkey_type}[],
                  identifiers := $8
                )
                """,
                self.cog_name,
                self.unique_cog_identifier,
                identifier_data.category,
                json.dumps(value),
                pkey_len,
                pkey_type,
                pkeys,
                list(identifier_data.identifiers),
            )
        except asyncpg.ErrorInAssignmentError:
            raise errors.CannotSetSubfield

    async def clear(self, identifier_data: IdentifierData):
        pkeys, pkey_type, pkey_len = self._get_pkey_info(identifier_data)
        try:
            await self._execute(
                f"""
                SELECT config.clear(
                  cog_name := $1,
                  cog_id := $2,
                  config_category := $3,
                  pkeys := $4::{pkey_type}[],
                  identifiers := $5
                )
                """,
                self.cog_name,
                self.unique_cog_identifier,
                identifier_data.category,
                pkeys,
                list(identifier_data.identifiers),
            )
        except asyncpg.UndefinedTableError:
            pass

    async def inc(
        self, identifier_data: IdentifierData, value: Union[int, float], default: Union[int, float]
    ) -> Union[int, float]:
        pkeys, pkey_type, pkey_len = self._get_pkey_info(identifier_data)
        try:
            return await self._execute(
                f"""
                SELECT config.inc(
                  cog_name := $1,
                  cog_id := $2,
                  config_category := $3,
                  amount := $4,
                  default_value := $5,
                  pkey_len := $6,
                  pkey_type := $7,
                  pkeys := $8::{pkey_type}[],
                  identifiers := $9
                )
                """,
                self.cog_name,
                self.unique_cog_identifier,
                identifier_data.category,
                value,
                default,
                pkey_len,
                pkey_type,
                pkeys,
                list(identifier_data.identifiers),
                method=self._pool.fetchval,
            )
        except asyncpg.WrongObjectTypeError as exc:
            raise errors.StoredTypeError(*exc.args)

    async def toggle(self, identifier_data: IdentifierData, default: bool) -> bool:
        pkeys, pkey_type, pkey_len = self._get_pkey_info(identifier_data)
        try:
            return await self._execute(
                f"""
                SELECT config.inc(
                  cog_name := $1,
                  cog_id := $2,
                  config_category := $3,
                  default_value := $4,
                  pkey_len := $5,
                  pkey_type := $6,
                  pkeys := $7::{pkey_type}[],
                  identifiers := $8
                )
                """,
                self.cog_name,
                self.unique_cog_identifier,
                identifier_data.category,
                default,
                pkey_len,
                pkey_type,
                pkeys,
                list(identifier_data.identifiers),
                method=self._pool.fetchval,
            )
        except asyncpg.WrongObjectTypeError as exc:
            raise errors.StoredTypeError(*exc.args)

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        query = "SELECT cog_name, cog_id FROM config.red_cogs"
        log.invisible(query)
        async with cls._pool.acquire() as conn, conn.transaction():
            async for row in conn.cursor(query):
                yield row["cog_name"], row["cog_id"]

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
            storage_details = data_manager.storage_details()
            await cls._pool.execute(f"DROP DATABASE $1", storage_details["database"])
        else:
            with DROP_DDL_SCRIPT_PATH.open() as fs:
                await cls._pool.execute(fs.read())

    @classmethod
    async def _execute(cls, query: str, *args, method: Optional[Callable] = None) -> Any:
        if method is None:
            method = cls._pool.execute
        log.invisible("Query: %s", query)
        if args:
            log.invisible("Args: %s", args)
        return await method(query, *args)

    @staticmethod
    def _get_pkey_info(identifier_data: IdentifierData) -> Tuple[List[Union[int, str]], str, int]:
        if identifier_data.category == ConfigCategory.GLOBAL.value:
            return [0], "bigint", 1
        elif identifier_data.is_custom:
            return list(identifier_data.primary_key), "text", identifier_data.primary_key_len
        else:
            return (
                list(map(int, identifier_data.primary_key)),
                "bigint",
                identifier_data.primary_key_len,
            )
