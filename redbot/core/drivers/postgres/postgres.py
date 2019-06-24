import getpass
import json
from pathlib import Path
from typing import Optional, Any, AsyncIterator, Tuple, Union, Callable, List

try:
    # pylint: disable=import-error
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


def encode_identifier_data(
    id_data: IdentifierData
) -> Tuple[str, str, str, List[str], List[str], int, bool]:
    return (
        id_data.cog_name,
        id_data.uuid,
        id_data.category,
        ["0"] if id_data.category == ConfigCategory.GLOBAL else list(id_data.primary_key),
        list(id_data.identifiers),
        1 if id_data.category == ConfigCategory.GLOBAL else id_data.primary_key_len,
        id_data.is_custom,
    )


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
        self, identifier_data: IdentifierData, value: Union[int, float], default: Union[int, float]
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
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        query = "SELECT cog_name, cog_id FROM red_config.red_cogs"
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
