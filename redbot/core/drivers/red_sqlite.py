from pathlib import Path
from typing import Tuple
import copy
import weakref
import logging
import sqlite3
import json

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

    def __init__(self, cog_name, identifier, **kwargs):
        super().__init__(cog_name, identifier)

        if self._conn is None:
            self._conn = self._initialize(kwargs)

        self._load_data()

    def _initialize(self, kwargs):
        db_name = kwargs.get("DB_NAME", "database.db")

        if db_name != ":memory:":
            db_path = Path.cwd() / "cogs" / ".data"
            db_path.mkdir(parents=True, exist_ok=True)
            db_path = db_path / db_name
        else:
            db_path = db_name

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(SQL_INIT)
        return conn

    @property
    def data(self):
        return _shared_datastore.get(self.cog_name)

    @data.setter
    def data(self, value):
        _shared_datastore[self.cog_name] = value

    def _load_data(self):
        if self.cog_name not in _driver_counts:
            _driver_counts[self.cog_name] = 0
        _driver_counts[self.cog_name] += 1

        _finalizers.append(weakref.finalize(self, finalize_driver, self.cog_name))

        if self.data is not None:
            return

        self.data = self._load_from_db()

    async def get(self, *identifiers: Tuple[str]):
        partial = self.data
        full_identifiers = (*identifiers,)
        for i in full_identifiers:
            partial = partial[i]
        return copy.deepcopy(partial)

    async def set(self, *identifiers: str, value=None):
        partial = self.data
        full_identifiers = (*identifiers,)
        for i in full_identifiers[:-1]:
            if i not in partial:
                partial[i] = {}
            partial = partial[i]

        partial[full_identifiers[-1]] = copy.deepcopy(value)
        self._update_db()

    async def clear(self, *identifiers: str):
        partial = self.data
        full_identifiers = (*identifiers,)
        try:
            for i in full_identifiers[:-1]:
                partial = partial[i]
            del partial[full_identifiers[-1]]
        except KeyError:
            pass
        else:
            self._update_db()

    def _update_db(self):
        data = json.dumps(self.data, **MINIFIED_JSON)

        cur = self._conn.cursor()
        result = cur.execute(
            SQL_UPDATE, (data, self.cog_name, self.unique_cog_identifier)
        )

        if result.rowcount == 0:
            result = cur.execute(
                SQL_INSERT, (self.cog_name, self.unique_cog_identifier, data)
            )

        self._conn.commit()

    def _load_from_db(self):
        cur = self._conn.cursor()

        result = cur.execute(SQL_SELECT, (self.cog_name, self.unique_cog_identifier))
        row = cur.fetchone()

        if row:
            return json.loads(row[0])
        else:
            return {}
