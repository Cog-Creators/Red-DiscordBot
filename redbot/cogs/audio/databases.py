import datetime
import json
import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import List, Dict, Union, Optional, Tuple


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

from .errors import InvalidTableError
from .utils import PlaylistScope
from .sql_statements import *

log = logging.getLogger("red.audio.database")

_config: Config = None
_bot: Red = None
database_connection: apsw.Connection = None
SCHEMA_VERSION = 3


_PARSER = {
    "youtube": {
        "insert": YOUTUBE_UPSERT,
        "youtube_url": {"query": YOUTUBE_QUERY},
        "update": YOUTUBE_UPDATE,
    },
    "spotify": {
        "insert": SPOTIFY_UPSERT,
        "track_info": {"query": SPOTIFY_QUERY},
        "update": SPOTIFY_UPDATE,
    },
    "lavalink": {
        "insert": LAVALINK_UPSERT,
        "data": {"query": LAVALINK_QUERY, "played": LAVALINK_QUERY_LAST_FETCHED_RANDOM},
        "update": LAVALINK_UPDATE,
    },
}


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


@dataclass
class PlaylistFetchResult:
    playlist_id: int
    playlist_name: str
    scope_id: int
    author_id: int
    playlist_url: Optional[str] = None
    tracks: List[dict] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = json.loads(self.tracks)


@dataclass
class CacheFetchResult:
    query: Optional[Union[str, dict]]
    last_updated: int

    def __post_init__(self):
        if isinstance(self.last_updated, int):
            self.updated_on: datetime.datetime = datetime.datetime.fromtimestamp(self.last_updated)
        if isinstance(self.query, str) and all(
            k in self.query for k in ["loadType", "playlistInfo", "isSeekable", "isStream"]
        ):
            self.query = json.loads(self.query)


@dataclass
class CacheLastFetchResult:
    tracks: List[dict] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = json.loads(self.tracks)


class CacheInterface:
    def __init__(self):
        self.database = database_connection.cursor()

    async def init(self):
        self.database.execute(PRAGMA_SET_temp_store)
        self.database.execute(PRAGMA_SET_journal_mode)
        self.database.execute(PRAGMA_SET_read_uncommitted)

        self.maybe_migrate()

        self.database.execute(LAVALINK_CREATE_TABLE)
        self.database.execute(LAVALINK_CREATE_INDEX)
        self.database.execute(YOUTUBE_CREATE_TABLE)
        self.database.execute(YOUTUBE_CREATE_INDEX)
        self.database.execute(SPOTIFY_CREATE_TABLE)
        self.database.execute(SPOTIFY_CREATE_INDEX)

        await self.clean_up_old_entries()

    async def clean_up_old_entries(self):
        max_age = await _config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values = {"maxage": maxage_int}
        self.database.execute(LAVALINK_DELETE_OLD_ENTRIES, values)
        self.database.execute(YOUTUBE_DELETE_OLD_ENTRIES, values)
        self.database.execute(SPOTIFY_DELETE_OLD_ENTRIES, values)

    def maybe_migrate(self):
        current_version = self.database.execute(PRAGMA_FETCH_user_version).fetchone()
        if isinstance(current_version, tuple):
            current_version = current_version[0]
        if not current_version:
            current_version = 1
        if current_version == SCHEMA_VERSION:
            return
        if current_version < 3 <= SCHEMA_VERSION:
            self.database.execute(SPOTIFY_DROP_TABLE)
            self.database.execute(YOUTUBE_DROP_TABLE)
            self.database.execute(LAVALINK_DROP_TABLE)

        self.database.execute(PRAGMA_SET_user_version, {"version": SCHEMA_VERSION})

    async def insert(self, table: str, values: List[dict]):
        try:
            if HAS_SQL:
                query = _PARSER.get(table, {}).get("insert")
                if query is None:
                    raise InvalidTableError(f"{table} is not a valid table in the database.")
                self.database.execute("BEGIN;")
                self.database.executemany(query, values)
                self.database.execute("COMMIT;")
        except Exception as err:
            log.debug("Error during audio db insert", exc_info=err)

    async def update(self, table: str, values: Dict[str, Union[str, int]]):
        try:
            if HAS_SQL:
                table = _PARSER.get(table, {})
                sql_query = table.get("update")
                time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
                values["last_fetched"] = time_now
                if not table:
                    raise InvalidTableError(f"{table} is not a valid table in the database.")
                self.database.execute(sql_query, values)
        except Exception as err:
            log.debug("Error during audio db update", exc_info=err)

    async def fetch_one(
        self, table: str, query: str, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[str], bool]:
        table = _PARSER.get(table, {})
        sql_query = table.get(query, {}).get("query")
        if HAS_SQL:
            if not table:
                raise InvalidTableError(f"{table} is not a valid table in the database.")
            max_age = await _config.cache_age()
            maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
                days=max_age
            )
            maxage_int = int(time.mktime(maxage.timetuple()))
            values.update({"maxage": maxage_int})
            output = self.database.execute(sql_query, values).fetchone() or (None, 0)
            result = CacheFetchResult(*output)
            return result.query, False
        else:
            return None, True

    async def fetch_all(
        self, table: str, query: str, values: Dict[str, Union[str, int]]
    ) -> List[CacheLastFetchResult]:
        if HAS_SQL:
            table = _PARSER.get(table, {})
            sql_query = table.get(query, {}).get("played")
            if not table:
                raise InvalidTableError(f"{table} is not a valid table in the database.")

            return [
                CacheLastFetchResult(*row)
                for row in self.database.execute(sql_query, values).fetchall()
            ]
        return []


class PlaylistInterface:
    def __init__(self):
        self.cursor = database_connection.cursor()
        self.cursor.execute(PRAGMA_SET_temp_store)
        self.cursor.execute(PRAGMA_SET_journal_mode)
        self.cursor.execute(PRAGMA_SET_read_uncommitted)
        self.cursor.execute(PLAYLIST_CREATE_TABLE)
        self.cursor.execute(PLAYLIST_CREATE_INDEX)

    @staticmethod
    def get_scope_type(scope: str) -> int:
        if scope == PlaylistScope.GLOBAL.value:
            table = 1
        elif scope == PlaylistScope.USER.value:
            table = 3
        else:
            table = 2
        return table

    def fetch(self, scope: str, playlist_id: int, scope_id: int) -> PlaylistFetchResult:
        scope_type = self.get_scope_type(scope)
        row = (
            self.cursor.execute(
                PLAYLIST_FETCH,
                ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type}),
            ).fetchone()
            or []
        )

        return PlaylistFetchResult(*row) if row else None

    def fetch_all(self, scope: str, scope_id: int, author_id=None) -> List[PlaylistFetchResult]:
        scope_type = self.get_scope_type(scope)
        if author_id is not None:
            output = self.cursor.execute(
                PLAYLIST_FETCH_ALL_WITH_FILTER,
                ({"scope_type": scope_type, "scope_id": scope_id, "author_id": author_id}),
            ).fetchall()
        else:
            output = self.cursor.execute(
                PLAYLIST_FETCH_ALL, ({"scope_type": scope_type, "scope_id": scope_id})
            ).fetchall()
        return [PlaylistFetchResult(*row) for row in output] if output else []

    def fetch_all_converter(
        self, scope: str, playlist_name, playlist_id
    ) -> List[PlaylistFetchResult]:
        scope_type = self.get_scope_type(scope)
        try:
            playlist_id = int(playlist_id)
        except:
            playlist_id = -1
        output = (
            self.cursor.execute(
                PLAYLIST_FETCH_ALL_CONVERTER,
                (
                    {
                        "scope_type": scope_type,
                        "playlist_name": playlist_name,
                        "playlist_id": playlist_id,
                    }
                ),
            ).fetchall()
            or []
        )
        return [PlaylistFetchResult(*row) for row in output] if output else []

    def delete(self, scope: str, playlist_id: int, scope_id: int):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(
            PLAYLIST_DELETE,
            ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type}),
        )

    def delete_scheduled(self):
        return self.cursor.execute(PLAYLIST_DELETE_SCHEDULED)

    def drop(self, scope: str):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(PLAYLIST_DELETE_SCOPE, ({"scope_type": scope_type}))

    def create_table(self, scope: str):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(PLAYLIST_CREATE_TABLE, ({"scope_type": scope_type}))

    def upsert(
        self,
        scope: str,
        playlist_id: int,
        playlist_name: str,
        scope_id: int,
        author_id: int,
        playlist_url: str,
        tracks: List[dict],
    ):
        scope_type = self.get_scope_type(scope)
        self.cursor.execute(
            PLAYLIST_UPSERT,
            (
                {
                    "scope_type": str(scope_type),
                    "playlist_id": int(playlist_id),
                    "playlist_name": str(playlist_name),
                    "scope_id": int(scope_id),
                    "author_id": int(author_id),
                    "playlist_url": playlist_url,
                    "tracks": json.dumps(tracks),
                }
            ),
        )
