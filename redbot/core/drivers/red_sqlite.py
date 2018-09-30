from pathlib import Path
from typing import Tuple
import copy
import weakref
import logging
import sqlite3
import json
import asyncio

SQL_INIT = (
    "CREATE TABLE IF NOT EXISTS data ("
    "cog_name text NOT NULL, "
    "identifier text NOT NULL, "
    "data text NOT NULL, "
    "PRIMARY KEY (cog_name, identifier)"
    ")  WITHOUT ROWID;"
)
SQL_SELECT = "SELECT data FROM data WHERE cog_name = ? AND identifier = ?;"
SQL_INSERT = "INSERT INTO data VALUES (?, ?, ?);"
SQL_UPDATE = "UPDATE data SET data = ? WHERE cog_name = ? AND identifier = ?;"

MINIFIED_JSON = {"sort_keys": False, "separators": (",", ":")}

from .red_base import BaseDriver

__all__ = ["SQLite"]

_shared_datastore = {}
_driver_counts = {}
_finalizers = []

loop = asyncio.get_event_loop()

log = logging.getLogger("redbot.sqlite_driver")


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

    def __init__(self, cog_name, identifier, **kwargs):
        super().__init__(cog_name, identifier)
        self._config_details = kwargs

    @property
    def data(self):
        return _shared_datastore.get(self.cog_name)

    @data.setter
    def data(self, value):
        _shared_datastore[self.cog_name] = value

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
        cur.execute(SQL_INIT)
        return conn

    def _load_data(self):
        if self.cog_name not in _driver_counts:
            _driver_counts[self.cog_name] = 0
        _driver_counts[self.cog_name] += 1

        _finalizers.append(weakref.finalize(self, finalize_driver, self.cog_name))

        if self.data is not None:
            return

        self.data = self._load_from_db()

    async def _initialize(self):
        # The connection is shared by every config instance.
        # This only gets called once
        if Sqlite._conn is None:
            async with Sqlite._lock:
                Sqlite._conn = self._connect()

        async with Sqlite._lock:
            await asyncio.wait([loop.run_in_executor(None, self._load_data)])

    async def get(self, *identifiers: Tuple[str]):
        if self.data is None:
            await self._initialize()

        partial = self.data
        full_identifiers = (*identifiers,)
        for i in full_identifiers:
            partial = partial[i]
        return copy.deepcopy(partial)

    async def set(self, *identifiers: str, value=None):
        if self.data is None:
            await self._initialize()

        partial = self.data
        full_identifiers = (*identifiers,)
        for i in full_identifiers[:-1]:
            if i not in partial:
                partial[i] = {}
            partial = partial[i]

        partial[full_identifiers[-1]] = copy.deepcopy(value)
        async with Sqlite._lock:
            await asyncio.wait([loop.run_in_executor(None, self._update_db)])

    async def clear(self, *identifiers: str):
        if self.data is None:
            await self._initialize()

        partial = self.data
        full_identifiers = (*identifiers,)
        try:
            for i in full_identifiers[:-1]:
                partial = partial[i]
            del partial[full_identifiers[-1]]
        except KeyError:
            pass
        else:
            async with Sqlite._lock:
                await asyncio.wait([loop.run_in_executor(None, self._update_db)])

    def _update_db(self):
        data = json.dumps(self.data, **MINIFIED_JSON)

        cur = Sqlite._conn.cursor()
        result = cur.execute(SQL_UPDATE, (data, self.cog_name, self.unique_cog_identifier))

        if result.rowcount == 0:
            result = cur.execute(SQL_INSERT, (self.cog_name, self.unique_cog_identifier, data))

        Sqlite._conn.commit()

    def _load_from_db(self):
        cur = Sqlite._conn.cursor()

        result = cur.execute(SQL_SELECT, (self.cog_name, self.unique_cog_identifier))
        row = cur.fetchone()

        if row:
            return json.loads(row[0])
        else:
            return {}
