import asyncio
import getpass
import itertools
import json
import weakref
from pathlib import Path
from typing import (
    Optional,
    Dict,
    Any,
    Set,
    Iterator,
    Sequence,
    Generator,
    AsyncIterator,
    Tuple,
    Union,
    Callable,
)

try:
    import asyncpg
except ModuleNotFoundError:
    asyncpg = None

from ... import errors
from ..base import BaseDriver, IdentifierData, ConfigCategory
from ..log import log

__all__ = ["PostgresDriver"]

_PKG_PATH = Path(__file__).parent
DDL_SCRIPT_PATH = _PKG_PATH / "ddl.sql"
DROP_DDL_SCRIPT_PATH = _PKG_PATH / "drop_ddl.sql"


class PostgresDriver(BaseDriver):

    _pool: Optional["asyncpg.pool.Pool"] = None
    _created_tables: Dict[str, Set[str]] = {}
    _table_creation_locks: Dict[str, asyncio.Lock] = weakref.WeakValueDictionary()
    _meta_created: bool = False

    def __init__(self, cog_name, identifier, **kwargs):
        self._schema_name: str = '"' + ".".join((cog_name, identifier)) + '"'

        super().__init__(cog_name, identifier, **kwargs)

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
        await self._maybe_create_table(identifier_data)

        table = ".".join((self._schema_name, identifier_data.category))

        ph_gen = self._gen_placeholders()
        pkey_len = self._get_pkey_len(identifier_data)
        pkeys = self._get_pkey(identifier_data)
        num_pkeys = len(pkeys)
        num_missing_pkeys = pkey_len - num_pkeys
        if num_missing_pkeys > 1:
            # Getting multiple rows across multiple wildcard primary key columns
            # Use (slower) custom aggregate function jsonb_agg_all
            missing_pkeys = ", ".join(
                (f"primary_key_{i}::text" for i in range(num_pkeys + 1, pkey_len + 1))
            )
            selection = f"jsonb_agg_all(json_data, {missing_pkeys})"
        elif num_missing_pkeys == 1:
            # Getting multiple rows across one wildcard primary key column
            # Use (faster) builtin aggregate function jsonb_object_agg
            selection = f"jsonb_object_agg(primary_key_{pkey_len}::text, json_data)"
        elif identifier_data.identifiers:
            # Getting a sub-key of a document
            id_ph = ", ".join(itertools.islice(ph_gen, len(identifier_data.identifiers)))
            # Prefer using jsonb_extract_path over -> or #> operators because it's easier to format
            # a query using a function with variadic parameters
            selection = f"jsonb_extract_path(json_data, {id_ph})"
        else:
            # Getting a whole document
            selection = "json_data"

        query = f"SELECT {selection} FROM {table}"
        if pkeys:
            query += self._create_whereclause(pkeys, ph_gen)
        result = await self._execute(
            query, *identifier_data.identifiers, *pkeys, method=self._pool.fetchval
        )

        if result is None:
            # The result is None both when postgres yields no results, or when it yields a NULL row
            # A 'null' JSON value would be returned as encoded JSON, i.e. the string 'null'
            raise KeyError
        return json.loads(result)

    async def set(self, identifier_data: IdentifierData, value=None):
        await self._maybe_create_table(identifier_data)

        table = ".".join((self._schema_name, identifier_data.category))

        ph_gen = self._gen_placeholders()
        pkeys = self._get_pkey(identifier_data)
        pkey_len = self._get_pkey_len(identifier_data)
        value_ph = ", ".join(itertools.islice(ph_gen, pkey_len + 1))
        if len(pkeys) < pkey_len:
            # Setting data for multiple rows.
            # This means some rows could be deleted and others updated, depending on what is in
            # `value`.
            # Safest and simplest way is to delete all rows matching the primary key, and then
            # insert all the new data.
            # We'll do it in a transaction incase something goes wrong between deleting and
            # inserting.
            if pkeys:
                ph_gen.send(1)
                whereclause = self._create_whereclause(pkeys, ph_gen)
            else:
                # Force rows to be deleted
                whereclause = " WHERE true"

            async with self._pool.acquire() as conn, conn.transaction():
                # Delete old rows
                await self._execute(
                    f"DELETE FROM {table}" + whereclause, *pkeys, method=conn.execute
                )
                # Insert updated rows
                await self._execute(
                    f"""
                    INSERT INTO {table} AS t VALUES({value_ph})
                    ON CONFLICT ON CONSTRAINT {identifier_data.category}_pkey DO NOTHING
                    """,
                    self._gen_rows(
                        value,
                        num_missing_keys=pkey_len - len(pkeys),
                        pkey_converter=str if identifier_data.is_custom else int,
                    ),
                    method=conn.executemany,
                )
            return
        elif identifier_data.identifiers:
            # Setting a whole document or a sub-key within a document.
            json_value_ph = next(ph_gen)
            id_ph = ", ".join(itertools.islice(ph_gen, len(identifier_data.identifiers)))
            # Full JSON if being inserted for the first time
            full_value = {}
            inner = full_value
            for i in identifier_data.identifiers[:-1]:
                inner = inner.setdefault(i, {})
            inner[identifier_data.identifiers[-1]] = value
            # Values encoded as JSON
            json_value = json.dumps(value)
            json_full_value = json.dumps(full_value)

            try:
                await self._execute(
                    f"""
                    INSERT INTO {table} AS t VALUES({value_ph})
                    ON CONFLICT ON CONSTRAINT {identifier_data.category}_pkey DO UPDATE SET 
                      json_data = (
                          SELECT jsonb_set_deep(t.json_data, {json_value_ph}::jsonb, {id_ph})
                      )
                    """,
                    *pkeys,
                    json_full_value,
                    json_value,
                    *identifier_data.identifiers,
                )
            except asyncpg.exceptions.ErrorInAssignmentError:
                raise errors.CannotSetSubfield
        else:
            # Setting a single document
            await self._execute(
                f"""
                INSERT INTO {table} VALUES({value_ph})
                ON CONFLICT ON CONSTRAINT {identifier_data.category}_pkey DO UPDATE SET
                  json_data = excluded.json_data
                """,
                *pkeys,
                json.dumps(value),
            )

    async def clear(self, identifier_data: IdentifierData):
        await self._maybe_create_table(identifier_data)

        table = ".".join((self._schema_name, identifier_data.category))
        ph_gen = self._gen_placeholders()
        pkeys = self._get_pkey(identifier_data)
        if identifier_data.identifiers:
            # Deleting key within document
            id_ph = ", ".join(itertools.islice(ph_gen, len(identifier_data.identifiers)))
            await self._execute(
                f"""
                UPDATE {table} AS t SET
                  json_data = (SELECT jsonb_clear(t.json_data, {id_ph}))
                {self._create_whereclause(pkeys, ph_gen)}
                """,
                *identifier_data.identifiers,
                *pkeys,
            )
        elif pkeys:
            # Deleting one or more documents from table
            await self._execute(
                f"DELETE FROM {table}" + self._create_whereclause(pkeys, ph_gen), *pkeys
            )
        elif identifier_data.category:
            # Deleting entire category
            await self._execute(f"DROP TABLE {table} CASCADE")
            self._created_tables[self._schema_name].remove(identifier_data.category)
        else:
            # Deleting all data
            await self._execute(f"DROP SCHEMA {self._schema_name} CASCADE")
            del self._created_tables[self._schema_name]

    @classmethod
    async def aiter_cogs(cls) -> AsyncIterator[Tuple[str, str]]:
        query = "SELECT cog_name, cog_id FROM red_cogs"
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
            async with cls._pool.acquire() as conn:
                settings = conn.get_settings()
                db_name = settings.database
                await conn.execute(f"DROP DATABASE $1", db_name)
        else:
            async with cls._pool.acquire() as conn, conn.transaction():
                async for cog_name, cog_id in cls.aiter_cogs():
                    schema_name = await conn.fetchval(
                        "SELECT schema_name FROM red_cogs WHERE cog_name = $1 AND cog_id = $2",
                        cog_name,
                        cog_id,
                    )
                    await conn.execute("DROP SCHEMA $1 CASCADE", schema_name)
                with DROP_DDL_SCRIPT_PATH.open() as fs:
                    await conn.execute(fs.read())

    async def _maybe_create_table(self, identifier_data: IdentifierData) -> None:
        """Create a table for the given category if needed.

        This will be an atomic operation within this driver's schema.
        """
        lock = self._table_creation_locks.setdefault(self._schema_name, asyncio.Lock())
        async with lock:
            schema_created = self._schema_name in self._created_tables
            if schema_created and (
                identifier_data.category in self._created_tables[self._schema_name]
                or not identifier_data.category
            ):
                return

            async with self._pool.acquire() as conn, conn.transaction():
                if not schema_created:
                    await self._execute(
                        f"CREATE SCHEMA IF NOT EXISTS {self._schema_name}", method=conn.execute
                    )
                    # Create entry in `red_cogs` table.
                    # The entry is removed by an event trigger when the schema is dropped.
                    await self._execute(
                        f"""
                        INSERT INTO red_cogs VALUES($1, $2, $3)
                        ON CONFLICT(cog_name, cog_id) DO NOTHING
                        """,
                        self.cog_name,
                        self.unique_cog_identifier,
                        self._schema_name.lower(),
                        method=conn.execute,
                    )
                    self._created_tables[self._schema_name] = set()
                if identifier_data.category:
                    pkey_type = "TEXT" if identifier_data.is_custom else "BIGINT"
                    pkey_len = self._get_pkey_len(identifier_data)
                    pkey_list = [f"primary_key_{i}" for i in range(1, pkey_len + 1)]
                    pkey_commalist = ", ".join(pkey_list)
                    pkey_commalist_with_type = ", ".join(
                        (" ".join((pkey, pkey_type)) for pkey in pkey_list)
                    )
                    table_name = ".".join((self._schema_name, identifier_data.category))
                    await self._execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                          {pkey_commalist_with_type},
                          json_data jsonb,
                          CONSTRAINT {identifier_data.category}_pkey PRIMARY KEY ({pkey_commalist})
                        )
                        """,
                        method=conn.execute,
                    )
                    self._created_tables[self._schema_name].add(identifier_data.category)

    @classmethod
    async def _execute(cls, query: str, *args, method: Optional[Callable] = None) -> Any:
        if method is None:
            method = cls._pool.execute
        log.invisible("Query: %s", query)
        if args:
            log.invisible("Args: %s", args)
        return await method(query, *args)

    @staticmethod
    def _create_whereclause(primary_keys: Sequence[str], ph_gen: Generator[str, int, None]) -> str:
        """Create a string for the WHERE clause in a query, based on the
        primary keys.

        The returned string won't include the actual primary keys, but
        placeholders for them, which are generated from the ``ph_gen``
        parameter.
        """
        return " WHERE " + " AND ".join(
            (f"primary_key_{i} = {next(ph_gen)}" for i in range(1, len(primary_keys) + 1))
        )

    @classmethod
    def _gen_rows(
        cls, value: Dict[str, Any], num_missing_keys: int, pkey_converter: Callable[[str], Any]
    ) -> Iterator[Sequence[Any]]:
        """Generate rows for multiple insertions into a table.

        This takes the dict as it is passed to the `BaseDriver.set`
        function, and should be used when some of the dict's keys are
        primary keys, thus it can contain data for multiple rows in a
        table. This dict has no intrinsic indication of which keys
        are primary keys and which are identifiers inside a document,
        so the ``num_missing_keys`` argument describes how many levels
        of the ``value`` dict are primary keys.

        The ``pkey_converter`` argument is called on primary keys.
        """
        # This is a recursive function
        if num_missing_keys == 1:
            # This is our base case, where we can simply yield (key, value) tuples
            for k, v in value.items():
                yield pkey_converter(k), json.dumps(v)
        else:
            for k, v in value.items():
                # If we need to yield (key, key, ..., value) tuples, we must recurse
                for row in cls._gen_rows(v, num_missing_keys - 1, pkey_converter):
                    yield (pkey_converter(k), *row)

    @staticmethod
    def _gen_placeholders() -> Generator[Optional[str], int, None]:
        """Generate placeholders in PostgreSQL prepared statements.

        Starts at '$1' and increments upon generation.

        The ``send()`` method of the generator resets the count to the
        passed `int`, and returns ``None``.
        """
        i = 1
        while True:
            recv = yield f"${i}"
            if recv is not None:
                i = recv
                yield
            else:
                i += 1

    @staticmethod
    def _get_pkey(identifier_data: IdentifierData) -> Tuple[Union[int, str], ...]:
        """Get the primary key from the given identifier data.

        The postgres driver uses this in place of
        `IdentifierData.primary_key` for the special cases of the GLOBAL
        category, and also to map keys as integers for non-custom
        groups.
        """
        if identifier_data.category == ConfigCategory.GLOBAL.value:
            return (0,)
        elif identifier_data.is_custom:
            return identifier_data.primary_key
        else:
            return tuple(map(int, identifier_data.primary_key))

    @staticmethod
    def _get_pkey_len(identifier_data):
        """Get the length of a full primary key for a particular category.

        The postgres driver uses this in place of
        `Identifierdata.primary_key_len` for the special case of the
        GLOBAL category, which has a primary key column to simplify
        insertions and updates.
        """
        if identifier_data.category == ConfigCategory.GLOBAL.value:
            # This is a special case for the postgres driver
            return 1
        else:
            return identifier_data.primary_key_len
