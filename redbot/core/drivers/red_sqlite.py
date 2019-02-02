from pathlib import Path
from typing import Tuple, Dict
from enum import Enum
from .red_base import BaseDriver
import logging
import sqlite3
import json
import asyncio


SQL_CREATE_GENERIC_TABLE = ( # Good for all categories but members
    "CREATE TABLE IF NOT EXISTS {tab_name} ("
    "id text NOT NULL, "
    "data text NOT NULL, "
    "PRIMARY KEY (id)"
    ")  WITHOUT ROWID;"
)

SQL_CREATE_MEMBER_TABLE = (
    "CREATE TABLE IF NOT EXISTS {tab_name} ("
    "id text NOT NULL, "
    "guild_id text NOT NULL, "
    "data text NOT NULL, "
    "PRIMARY KEY (id, guild_id)"
    ")  WITHOUT ROWID;"
)

SQL_GENERIC_TABLE_SELECT     = "SELECT data FROM {tab_name} WHERE id = ?;"
SQL_GENERIC_TABLE_SELECT_ALL = "SELECT id, data FROM {tab_name};"
SQL_GENERIC_TABLE_INSERT     = "INSERT INTO {tab_name} VALUES (?, ?);"
SQL_GENERIC_TABLE_UPDATE     = "UPDATE {tab_name} SET data = ? WHERE id = ?;"
SQL_GENERIC_TABLE_DELETE     = "DELETE FROM {tab_name} WHERE id = ?;"

SQL_MEMBER_TABLE_SELECT      = "SELECT data FROM {tab_name} WHERE id = ? AND guild_id = ?;"
SQL_MEMBER_TABLE_SELECT_ALL  = "SELECT id, guild_id, data FROM {tab_name};"
SQL_MEMBER_TABLE_INSERT      = "INSERT INTO {tab_name} VALUES (?, ?, ?);"
SQL_MEMBER_TABLE_UPDATE      = "UPDATE {tab_name} SET data = ? WHERE id = ? AND guild_id = ?;"
SQL_MEMBER_TABLE_DELETE      = "DELETE FROM {tab_name} WHERE id = ? AND guild_id = ?;"

SQL_LIST_TABLES = "SELECT name FROM sqlite_master;"
SQL_DROP_TABLE = "DROP TABLE {tab_name};"

MINIFIED_JSON = {"sort_keys": False, "separators": (",", ":")}

__all__ = ["SQLite"]

loop = asyncio.get_event_loop()
log = logging.getLogger("redbot.sqlite_driver")


class DataCategories(Enum):
    """Config categories"""
    _global = "GLOBAL"
    guild = "GUILD"
    channel = "TEXTCHANNEL"
    role = "ROLE"
    user = "USER"
    member = "MEMBER"


class Sqlite(BaseDriver):
    """
    Subclass of :py:class:`.red_base.BaseDriver`.

    .. py:attribute:: file_name

        The name of the SQLite database file.

    .. py:attribute:: data_path

        The path in which to store the file indicated by :py:attr:`file_name`.
    """

    _conn: sqlite3.Connection = None
    _lock = asyncio.Lock()
    _db_tables = []

    def __init__(self, cog_name, identifier, **kwargs):
        super().__init__(cog_name, identifier)
        self._config_details = kwargs
        self.initialized = False

    def _connect(self):
        db_name = self._config_details.get("DB_NAME", "database.db")
        path = self._config_details.get("data_path_override")

        if path:
            # Here I'm assuming that the data_path_override is always
            # going to be <user_chosen_folder>/core.
            # I'm getting the parent folder, which would be the root of
            # the user chosen folder, to open the db there
            path = path.parents[0]
        else:
            path = Path.cwd()

        if db_name != ":memory:":
            path.mkdir(parents=True, exist_ok=True)
            path = path / db_name
        else:
            path = db_name

        conn = sqlite3.connect(str(path), check_same_thread=False)
        cur = conn.cursor()
        return conn

    async def _initialize(self):
        async with Sqlite._lock:
            if Sqlite._conn is None:
                # The connection is shared by every config instance.
                # This only gets called once
                Sqlite._conn = self._connect()

            cur = Sqlite._conn.cursor()
            cur.execute("PRAGMA journal_mode=wal")
            self._db_tables = self._list_tables()

        self.initialized = True

    async def get(self, *identifiers: Tuple[str]):
        if self.initialized is False:
            await self._initialize()

        category = identifiers[0]
        tab_name = self._get_table_name(category)

        if tab_name not in self._db_tables:
            raise KeyError()

        if len(identifiers) == 1:
            return await self._get_all(category, tab_name)

        if category == DataCategories.member.value:
            offset = 3
            ident = (identifiers[1], identifiers[2])
            select = SQL_MEMBER_TABLE_SELECT
        else:
            offset = 2
            ident = (identifiers[1],)
            select = SQL_GENERIC_TABLE_SELECT

        cur = Sqlite._conn.cursor()
        cur.execute(select.format(tab_name=tab_name), ident)
        row = cur.fetchone()

        if row:
            data = json.loads(row[0])
        else:
            raise KeyError()

        ident = identifiers[offset:]
        for i in ident:
            data = data[i]

        return data

    async def _get_all(self, category, tab_name)->Dict:
        is_member_tab = category == DataCategories.member.value

        if is_member_tab:
            select_all = SQL_MEMBER_TABLE_SELECT_ALL
        else:
            select_all = SQL_GENERIC_TABLE_SELECT_ALL

        select_all = select_all.format(tab_name=tab_name)

        cur = Sqlite._conn.cursor()
        cur.execute(select_all)
        all_data = cur.fetchall()
        out = {}

        if is_member_tab:
            for row in all_data:
                user_id, guild_id, data = row[0], row[1], row[2]
                if guild_id not in out:
                    out[guild_id] = {}
                out[guild_id][user_id] = json.loads(data)
        else:
            for row in all_data:
                _id, data = row[0], row[1]
                out[_id] = json.loads(data)

        return out

    async def set(self, *identifiers: Tuple[str], value=None):
        if self.initialized is False:
            await self._initialize()

        category = identifiers[0]
        tab_name = self._get_table_name(category)

        if tab_name not in self._db_tables:
            await self._create_table_(category, tab_name)

        if category == DataCategories.member.value:
            is_replacing_data = not len(identifiers) > 3
            ident = (identifiers[2], identifiers[1])
            insert = SQL_MEMBER_TABLE_INSERT
            update = SQL_MEMBER_TABLE_UPDATE
        else:
            is_replacing_data = not len(identifiers) > 2
            ident = (identifiers[1],)
            insert = SQL_GENERIC_TABLE_INSERT
            update = SQL_GENERIC_TABLE_UPDATE

        if not is_replacing_data:
            # Updating data means fetching it, setting the new value
            # inside the dict and writing it back
            await self._update_data(identifiers, value)
            return

        data = json.dumps(value, **MINIFIED_JSON)

        cur = Sqlite._conn.cursor()

        async with Sqlite._lock:
            result = cur.execute(update.format(tab_name=tab_name),
                                 (data, *ident))
            if result.rowcount == 0:
                cur.execute(insert.format(tab_name=tab_name),
                            (*ident, data))
            Sqlite._conn.commit()

    async def _update_data(self, identifiers, value):
        category = identifiers[0]
        if category == DataCategories.member.value:
            offset = 3
        else:
            offset = 2

        try:
            data = await self.get(*identifiers[:offset])
        except KeyError:
            data = {}

        original_data = data

        for i in identifiers[offset:-1]:
            if i not in data:
                data[i] = {}
            data = data[i]

        data[identifiers[-1]] = value

        await self.set(*identifiers[:offset], value=original_data)

    async def clear(self, *identifiers: Tuple[str]):
        if self.initialized is False:
            await self._initialize()

        length = len(identifiers)
        if length == 0:
            await self._drop_all_tables()
            return

        category = identifiers[0]
        tab_name = self._get_table_name(category)

        if tab_name not in self._db_tables:
            return

        if length == 1:
            return await self._drop_table(tab_name)

        is_member_cat = category == DataCategories.member

        if is_member_cat:
            offset = 3
        else:
            offset = 2

        is_nested = length > offset

        if is_nested:
            # If it's a nested value we need to fetch the row,
            # delete the value inside the blob and write it back
            await self._clear_nested_value(tab_name, identifiers, is_member_cat)
        else:
            # Since it's not nested we can just delete the row
            await self._clear_row(tab_name, identifiers, is_member_cat)

    async def _drop_table(self, tab_name):
        cur = Sqlite._conn.cursor()

        async with self._lock:
            cur.execute(SQL_DROP_TABLE.format(tab_name=tab_name))
            Sqlite._conn.commit()
            self._db_tables.remove(tab_name)

    async def _drop_all_tables(self):
        to_remove = []
        cur = Sqlite._conn.cursor()

        async with self._lock:
            for c in DataCategories:
                tab_name = self._get_table_name(c.value)
                if tab_name in self._db_tables:
                    cur.execute(SQL_DROP_TABLE.format(tab_name=tab_name))
                    to_remove.append(tab_name)

            Sqlite._conn.commit()

            for tab_name in to_remove:
                self._db_tables.remove(tab_name)

    async def _clear_nested_value(self, tab_name, identifiers, is_member_cat):
        if is_member_cat:
            offset = 3
        else:
            offset = 2

        ident = identifiers[:offset]
        data = await self.get(*ident) # Let's get the data first

        original_data = data

        for k in identifiers[offset:-1]:
            data = data[k]

        del data[identifiers[-1]] # The value in original_data goes poof

        ident = identifiers[:offset]
        await self.set(*ident, value=original_data) # And now let's write it back

    async def _clear_row(self, tab_name, identifiers, is_member_cat):
        cur = Sqlite._conn.cursor()

        if is_member_cat:
            delete = SQL_MEMBER_TABLE_DELETE
        else:
            delete = SQL_GENERIC_TABLE_DELETE

        async with Sqlite._lock:
            cur.execute(delete.format(tab_name=tab_name), identifiers[1:])
            Sqlite._conn.commit()

    def _list_tables(self):
        cur = Sqlite._conn.cursor()
        cur.execute(SQL_LIST_TABLES)
        tables = cur.fetchall()
        return [t[0] for t in tables]

    async def _create_table_(self, category, table_name):
        cur = self._conn.cursor()

        if category == DataCategories.member.value:
            schema = SQL_CREATE_MEMBER_TABLE
        else:
            schema = SQL_CREATE_GENERIC_TABLE

        async with Sqlite._lock:
            cur.execute(schema.format(tab_name=table_name))
            self._db_tables.append(table_name)

    def _get_table_name(self, category):
        return "{}_{}_{}".format(
            self.cog_name.lower(),
            self.unique_cog_identifier,
            category.lower()
            )
