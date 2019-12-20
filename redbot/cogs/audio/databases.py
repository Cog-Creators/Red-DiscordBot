import datetime
import time
import traceback
from typing import List, Dict, Union, Optional, Tuple

from redbot.cogs.audio.errors import InvalidTableError

try:
    import apsw

    SQLError = apsw.ExecutionCompleteError
    HAS_SQL = True
    _ERROR = None
except ImportError as err:
    _ERROR = "".join(traceback.format_exception_only(type(err), err)).strip()
    HAS_SQL = False
    SQLError = err.__class__
    apsw = None


from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path

_DROP_YOUTUBE_TABLE = """
DROP TABLE IF EXISTS youtube;
"""
_CREATE_YOUTUBE_TABLE = """
CREATE TABLE IF NOT EXISTS youtube(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_info TEXT,
    youtube_url TEXT,
    last_updated INTEGER,
    last_fetched INTEGER
);
"""
_CREATE_UNIQUE_INDEX_YOUTUBE_TABLE = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_youtube_url 
ON youtube (track_info, youtube_url);
"""
_INSERT_YOUTUBE_TABLE = """INSERT INTO 
youtube 
  (
    track_info,  
    youtube_url,
    last_updated,
    last_fetched
  ) 
VALUES 
  (
   :track_info, 
   :track_url,
   :last_updated,
   :last_fetched
  )
ON CONFLICT
  (
  track_info, 
  youtube_url
  )
DO UPDATE 
  SET 
    track_info = excluded.track_info, 
    last_updated = excluded.last_updated
"""
_UPDATE_YOUTUBE_TABLE = """
UPDATE youtube
SET last_fetched=:last_fetched 
WHERE track_info=:track;
"""
_QUERY_YOUTUBE_TABLE = """
SELECT track_info, last_updated
FROM youtube 
WHERE 
    track_info=:track
    AND last_updated > :maxage
;
"""
_DROP_SPOTIFY_TABLE = """
DROP TABLE IF EXISTS spotify;
"""
_CREATE_UNIQUE_INDEX_SPOTIFY_TABLE = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_spotify_uri 
ON spotify (id, type, uri);
"""
_CREATE_SPOTIFY_TABLE = """
CREATE TABLE IF NOT EXISTS spotify(
    id TEXT,
    type TEXT,
    uri TEXT,
    track_name TEXT,
    artist_name TEXT, 
    song_url TEXT,
    track_info TEXT,
    last_updated INTEGER,
    last_fetched INTEGER
);
"""
_INSERT_SPOTIFY_TABLE = """INSERT INTO 
spotify 
  (
    id, type, uri, track_name, artist_name, 
    song_url, track_info, last_updated, last_fetched
  ) 
VALUES 
  (
    :id, :type, :uri, :track_name, :artist_name, 
    :song_url, :track_info, :last_updated, :last_fetched
  )
ON CONFLICT
  (
    id,
    type,
    uri
  ) 
DO UPDATE 
  SET 
    track_name = excluded.track_name,
    artist_name = excluded.artist_name,
    song_url = excluded.song_url,
    track_info = excluded.track_info,
    last_updated = excluded.last_updated;
"""
_QUERY_SPOTIFY_TABLE = """
SELECT track_info, last_updated
FROM spotify 
WHERE 
    uri=:uri
    AND last_updated > :maxage;
"""
_UPDATE_SPOTIFY_TABLE = """
UPDATE spotify
SET last_fetched=:last_fetched 
WHERE uri=:uri;
"""
_DROP_LAVALINK_TABLE = """
DROP TABLE IF EXISTS lavalink ;
"""
_CREATE_LAVALINK_TABLE = """
CREATE TABLE IF NOT EXISTS lavalink(
    query TEXT,
    data JSON,
    last_updated INTEGER,
    last_fetched INTEGER

);
"""
_CREATE_UNIQUE_INDEX_LAVALINK_TABLE = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_lavalink_query 
ON lavalink (query);
"""
_INSERT_LAVALINK_TABLE = """INSERT INTO 
lavalink 
  (
    query,  
    data, 
    last_updated, 
    last_fetched
  ) 
VALUES 
  (
   :query, 
   :data,
   :last_updated, 
   :last_fetched
  )
ON CONFLICT
  (
    query
  ) 
DO UPDATE 
  SET 
    data = excluded.data,
    last_updated = excluded.last_updated;
"""
_UPDATE_LAVALINK_TABLE = """
UPDATE lavalink
SET last_fetched=:last_fetched 
WHERE query=:query;
"""
_QUERY_LAVALINK_TABLE = """
SELECT data, last_updated
FROM lavalink 
WHERE 
    query=:query
    AND last_updated > :maxage;
"""
_QUERY_LAST_FETCHED_LAVALINK_TABLE = """
SELECT data
FROM lavalink 
WHERE 
    last_fetched > :day
    AND last_updated > :maxage
ORDER BY RANDOM()
LIMIT 10
;
"""
_PARSER = {
    "youtube": {
        "insert": _INSERT_YOUTUBE_TABLE,
        "youtube_url": {"query": _QUERY_YOUTUBE_TABLE},
        "update": _UPDATE_YOUTUBE_TABLE,
    },
    "spotify": {
        "insert": _INSERT_SPOTIFY_TABLE,
        "track_info": {"query": _QUERY_SPOTIFY_TABLE},
        "update": _UPDATE_SPOTIFY_TABLE,
    },
    "lavalink": {
        "insert": _INSERT_LAVALINK_TABLE,
        "data": {"query": _QUERY_LAVALINK_TABLE, "played": _QUERY_LAST_FETCHED_LAVALINK_TABLE},
        "update": _UPDATE_LAVALINK_TABLE,
    },
}
_PRAGMA_UPDATE_temp_store = """
PRAGMA temp_store = 2;
"""
_PRAGMA_UPDATE_journal_mode = """
PRAGMA journal_mode = wal;
"""
_PRAGMA_UPDATE_read_uncommitted = """
PRAGMA read_uncommitted = 1;
"""
_PRAGMA_FETCH_user_version = """
pragma user_version;
"""
_PRAGMA_SET_user_version = """
pragma user_version = :version;
"""
_DELETE_LAVALINK_OLD = """
DELETE FROM lavalink 
WHERE 
    last_updated > :maxage;
"""
_DELETE_YOUTUBE_OLD = """
DELETE FROM youtube 
WHERE 
    last_updated > :maxage;
"""
_DELETE_SPOTIFY_OLD = """
DELETE FROM spotify 
WHERE 
    last_updated > :maxage;
"""

_config: Config = None
_bot: Red = None
database_connection: apsw.Connection = None
SCHEMA_VERSION = 3


def _pass_config_to_databases(config: Config, bot: Red):
    global _config, _bot, database_connection
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot
    if database_connection is None:
        database_connection = apsw.Connection(
            str(cog_data_path(_bot.get_cog("Audio")) / "Audio.db")
        )


class CacheInterface:
    def __init__(self):
        self.database = database_connection.cursor()

    async def init(self):
        self.database.execute(_PRAGMA_UPDATE_temp_store)
        self.database.execute(_PRAGMA_UPDATE_journal_mode)
        self.database.execute(_PRAGMA_UPDATE_read_uncommitted)

        self.maybe_migrate()

        self.database.execute(_CREATE_LAVALINK_TABLE)
        self.database.execute(_CREATE_UNIQUE_INDEX_LAVALINK_TABLE)
        self.database.execute(_CREATE_YOUTUBE_TABLE)
        self.database.execute(_CREATE_UNIQUE_INDEX_YOUTUBE_TABLE)
        self.database.execute(_CREATE_SPOTIFY_TABLE)
        self.database.execute(_CREATE_UNIQUE_INDEX_SPOTIFY_TABLE)

        await self.clean_up_old_entries()

    async def clean_up_old_entries(self):
        max_age = await _config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values = {"maxage": maxage_int}
        self.database.execute(_DELETE_LAVALINK_OLD, values)
        self.database.execute(_DELETE_YOUTUBE_OLD, values)
        self.database.execute(_DELETE_SPOTIFY_OLD, values)

    def maybe_migrate(self):
        current_version = self.database.execute(_PRAGMA_FETCH_user_version).fetchone()
        if not current_version:
            current_version = 1
        if current_version == SCHEMA_VERSION:
            return
        if current_version < 3 <= SCHEMA_VERSION:
            self.database.execute(_DROP_SPOTIFY_TABLE)
            self.database.execute(_DROP_YOUTUBE_TABLE)
            self.database.execute(_DROP_LAVALINK_TABLE)

        self.database.execute(_PRAGMA_SET_user_version, {"version": SCHEMA_VERSION})

    async def insert(self, table: str, values: List[dict]):
        if HAS_SQL:
            query = _PARSER.get(table, {}).get("insert")
            if query is None:
                raise InvalidTableError(f"{table} is not a valid table in the database.")
            self.database.executemany(query, values)

    async def update(self, table: str, values: Dict[str, Union[str, int]]):
        if HAS_SQL:
            table = _PARSER.get(table, {})
            sql_query = table.get("update")
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            values["last_fetched"] = time_now
            if not table:
                raise InvalidTableError(f"{table} is not a valid table in the database.")
            self.database.execute(sql_query, values)

    async def fetch_one(
        self, table: str, query: str, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[str], bool]:
        table = _PARSER.get(table, {})
        sql_query = table.get(query, {}).get("query")
        need_update = False
        if HAS_SQL:
            if not table:
                raise InvalidTableError(f"{table} is not a valid table in the database.")
            max_age = await _config.cache_age()
            maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
                days=max_age
            )
            maxage_int = int(time.mktime(maxage.timetuple()))
            values.update({"maxage": maxage_int})
            query, last_updated = self.database.execute(sql_query, values).fetchone() or (
                None,
                None,
            )
            return query or None, need_update if table != "spotify" else True
        else:
            return None, True

    async def fetch_all(
        self, table: str, query: str, values: Dict[str, Union[str, int]]
    ) -> List[Tuple[str, str]]:
        if HAS_SQL:
            table = _PARSER.get(table, {})
            sql_query = table.get(query, {}).get("played")
            if not table:
                raise InvalidTableError(f"{table} is not a valid table in the database.")

            return self.database.execute(sql_query, values).fetchall()
        return []
