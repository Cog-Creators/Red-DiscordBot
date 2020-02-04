import asyncio
import concurrent.futures
import contextlib
import datetime
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple, Union, MutableMapping, Mapping

import apsw
import lavalink

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.dbtools import APSWConnectionWrapper

from .debug import is_debug, debug_exc_log
from .errors import InvalidTableError
from .sql_statements import *
from .utils import PlaylistScope, track_to_json

log = logging.getLogger("red.cogs.Audio.database")

if TYPE_CHECKING:
    database_connection: APSWConnectionWrapper
    _bot: Red
    _config: Config
else:
    _config = None
    _bot = None
    database_connection = None


SCHEMA_VERSION = 3
SQLError = apsw.ExecutionCompleteError

IS_DEBUG = is_debug()

_PARSER: Mapping = {
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
        database_connection = APSWConnectionWrapper(
            str(cog_data_path(_bot.get_cog("Audio")) / "Audio.db")
        )


@dataclass
class PlaylistFetchResult:
    playlist_id: int
    playlist_name: str
    scope_id: int
    author_id: int
    playlist_url: Optional[str] = None
    tracks: List[MutableMapping] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = json.loads(self.tracks)


@dataclass
class QueueFetchResult:
    guild_id: int
    room_id: int
    track: dict = field(default_factory=lambda: {})
    track_object: lavalink.Track = None

    def __post_init__(self):
        if isinstance(self.track, str):
            self.track = json.loads(self.track)
        if self.track:
            self.track_object = lavalink.Track(self.track)


@dataclass
class CacheFetchResult:
    query: Optional[Union[str, MutableMapping]]
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
    tracks: List[MutableMapping] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = json.loads(self.tracks)


@dataclass
class CacheGetAllLavalink:
    query: str
    data: List[MutableMapping] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.data, str):
            self.data = json.loads(self.data)


class CacheInterface:
    def __init__(self):
        self.database_cursor = database_connection.cursor()
        self._database = database_connection

    @staticmethod
    def close():
        with contextlib.suppress(Exception):
            database_connection.close()

    async def init(self):
        self._database.cursor().execute(PRAGMA_SET_temp_store)
        self._database.cursor().execute(PRAGMA_SET_journal_mode)
        self._database.cursor().execute(PRAGMA_SET_read_uncommitted)
        self.maybe_migrate()

        self._database.cursor().execute(LAVALINK_CREATE_TABLE)
        self._database.cursor().execute(LAVALINK_CREATE_INDEX)
        self._database.cursor().execute(YOUTUBE_CREATE_TABLE)
        self._database.cursor().execute(YOUTUBE_CREATE_INDEX)
        self._database.cursor().execute(SPOTIFY_CREATE_TABLE)
        self._database.cursor().execute(SPOTIFY_CREATE_INDEX)

        await self.clean_up_old_entries()

    async def clean_up_old_entries(self):
        max_age = await _config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values = {"maxage": maxage_int}
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self._database.cursor().execute, LAVALINK_DELETE_OLD_ENTRIES, values)
            executor.submit(self._database.cursor().execute, YOUTUBE_DELETE_OLD_ENTRIES, values)
            executor.submit(self._database.cursor().execute, SPOTIFY_DELETE_OLD_ENTRIES, values)

    def maybe_migrate(self):
        current_version = self._database.cursor().execute(PRAGMA_FETCH_user_version).fetchone()
        if isinstance(current_version, tuple):
            current_version = current_version[0]
        if current_version == SCHEMA_VERSION:
            return
        self._database.cursor().execute(PRAGMA_SET_user_version, {"version": SCHEMA_VERSION})

    async def insert(self, table: str, values: List[MutableMapping]):
        try:
            query = _PARSER.get(table, {}).get("insert")
            if query is None:
                raise InvalidTableError(f"{table} is not a valid table in the database.")
            with self._database.transaction() as transaction:
                transaction.executemany(query, values)
        except Exception as err:
            debug_exc_log(log, err, "Error during audio db insert")

    async def update(self, table: str, values: Dict[str, Union[str, int]]):
        try:
            table = _PARSER.get(table, {})
            sql_query = table.get("update")
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            values["last_fetched"] = time_now
            if not table:
                raise InvalidTableError(f"{table} is not a valid table in the database.")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(self._database.cursor().execute, sql_query, values)
        except Exception as err:
            debug_exc_log(log, err, "Error during audio db update")

    async def fetch_one(
        self, table: str, query: str, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[str], bool]:
        table = _PARSER.get(table, {})
        sql_query = table.get(query, {}).get("query")
        if not table:
            raise InvalidTableError(f"{table} is not a valid table in the database.")
        max_age = await _config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values.update({"maxage": maxage_int})
        row = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self._database.cursor().execute, sql_query, values)]
            ):
                try:
                    row_result = future.result()
                    row = row_result.fetchone()
                except Exception as exc:
                    debug_exc_log(log, exc, "Failed to completed fetch from database")
        if not row:
            return None, False
        return CacheFetchResult(*row).query, False

    async def fetch_all(
        self, table: str, query: str, values: Dict[str, Union[str, int]]
    ) -> List[CacheLastFetchResult]:
        table = _PARSER.get(table, {})
        sql_query = table.get(query, {}).get("played")
        if not table:
            raise InvalidTableError(f"{table} is not a valid table in the database.")
        output = []
        row_result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self._database.cursor().execute, sql_query, values)]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    debug_exc_log(log, exc, "Failed to completed random fetch from database")
        for index, row in enumerate(row_result, start=1):
            if index % 50 == 0:
                await asyncio.sleep(0.01)
            output.append(CacheLastFetchResult(*row))
            await asyncio.sleep(0)
        return output

    async def fetch_random(
        self, table: str, query: str, values: Dict[str, Union[str, int]]
    ) -> CacheLastFetchResult:
        table = _PARSER.get(table, {})
        sql_query = table.get(query, {}).get("played")
        if not table:
            raise InvalidTableError(f"{table} is not a valid table in the database.")

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self._database.cursor().execute, sql_query, values)]
            ):
                try:
                    row = future.result()
                    row = row.fetchone()
                except Exception as err:
                    debug_exc_log(log, err, "Failed to completed random fetch from database")
        return CacheLastFetchResult(*row)

    async def fetch_all_for_global(self) -> List[CacheGetAllLavalink]:
        output = []
        row_result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [
                    executor.submit(
                        self._database.cursor().execute, LAVALINK_FETCH_ALL_ENTRIES_GLOBAL
                    )
                ]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    debug_exc_log(log, exc, "Failed to completed random fetch from database")
        for index, row in enumerate(row_result, start=1):
            if index % 50 == 0:
                await asyncio.sleep(0.01)
            output.append(CacheGetAllLavalink(*row))
            await asyncio.sleep(0)
        return output


class PlaylistInterface:
    def __init__(self):
        self.database = database_connection
        self.cursor = database_connection.cursor()
        self.cursor.execute(PRAGMA_SET_temp_store)
        self.cursor.execute(PRAGMA_SET_journal_mode)
        self.cursor.execute(PRAGMA_SET_read_uncommitted)
        self.cursor.execute(PLAYLIST_CREATE_TABLE)
        self.cursor.execute(PLAYLIST_CREATE_INDEX)

    @staticmethod
    def close():
        with contextlib.suppress(Exception):
            database_connection.close()

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

    async def fetch_all(
        self, scope: str, scope_id: int, author_id=None
    ) -> List[PlaylistFetchResult]:
        scope_type = self.get_scope_type(scope)
        output = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            if author_id is not None:
                for future in concurrent.futures.as_completed(
                    [
                        executor.submit(
                            self.database.cursor().execute,
                            PLAYLIST_FETCH_ALL_WITH_FILTER,
                            (
                                {
                                    "scope_type": scope_type,
                                    "scope_id": scope_id,
                                    "author_id": author_id,
                                }
                            ),
                        )
                    ]
                ):
                    try:
                        row_result = future.result()
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed playlist fetch from database")
                        return []
            else:
                for future in concurrent.futures.as_completed(
                    [
                        executor.submit(
                            self.database.cursor().execute,
                            PLAYLIST_FETCH_ALL,
                            ({"scope_type": scope_type, "scope_id": scope_id}),
                        )
                    ]
                ):
                    try:
                        row_result = future.result()
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed playlist fetch from database")
                        return []

        for index, row in enumerate(row_result, start=1):
            if index % 50 == 0:
                await asyncio.sleep(0.01)
            output.append(PlaylistFetchResult(*row))
            await asyncio.sleep(0)
        return output

    async def fetch_all_converter(
        self, scope: str, playlist_name, playlist_id
    ) -> List[PlaylistFetchResult]:
        scope_type = self.get_scope_type(scope)
        try:
            playlist_id = int(playlist_id)
        except Exception as exc:
            debug_exc_log(log, exc, "Failed converting playlist_id to int")
            playlist_id = -1

        output = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [
                    executor.submit(
                        self.database.cursor().execute,
                        PLAYLIST_FETCH_ALL_CONVERTER,
                        (
                            {
                                "scope_type": scope_type,
                                "playlist_name": playlist_name,
                                "playlist_id": playlist_id,
                            }
                        ),
                    )
                ]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    debug_exc_log(log, exc, "Failed to completed fetch from database")

            for index, row in enumerate(row_result, start=1):
                if index % 50 == 0:
                    await asyncio.sleep(0.01)
                output.append(PlaylistFetchResult(*row))
                await asyncio.sleep(0)
        return output

    def delete(self, scope: str, playlist_id: int, scope_id: int):
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.cursor.execute,
                PLAYLIST_DELETE,
                ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type}),
            )

    def delete_scheduled(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.cursor.execute, PLAYLIST_DELETE_SCHEDULED)

    def drop(self, scope: str):
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.cursor.execute, PLAYLIST_DELETE_SCOPE, ({"scope_type": scope_type})
            )

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
        playlist_url: Optional[str],
        tracks: List[MutableMapping],
    ):
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.cursor.execute,
                PLAYLIST_UPSERT,
                {
                    "scope_type": str(scope_type),
                    "playlist_id": int(playlist_id),
                    "playlist_name": str(playlist_name),
                    "scope_id": int(scope_id),
                    "author_id": int(author_id),
                    "playlist_url": playlist_url,
                    "tracks": json.dumps(tracks),
                },
            )


class QueueInterface:
    def __init__(self):
        self.cursor = database_connection.cursor()
        self.database = database_connection
        self.cursor.execute(PRAGMA_SET_temp_store)
        self.cursor.execute(PRAGMA_SET_journal_mode)
        self.cursor.execute(PRAGMA_SET_read_uncommitted)
        self.cursor.execute(PERSIST_QUEUE_CREATE_TABLE)
        self.cursor.execute(PERSIST_QUEUE_CREATE_INDEX)

    @staticmethod
    def close():
        with contextlib.suppress(Exception):
            database_connection.close()

    async def fetch(self) -> List[QueueFetchResult]:
        output = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, PERSIST_QUEUE_FETCH_ALL,)]
            ):
                try:
                    row_result = future.result()
                except Exception as exc:
                    debug_exc_log(log, exc, "Failed to completed fetch from database")

            for index, row in enumerate(row_result, start=1):
                if index % 50 == 0:
                    await asyncio.sleep(0.01)
                output.append(QueueFetchResult(*row))
                await asyncio.sleep(0)
        return output

    def played(self, guild_id: int, track_id: str):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.cursor.execute,
                PERSIST_QUEUE_PLAYED,
                {"guild_id": guild_id, "track_id": track_id},
            )

    def delete_scheduled(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.cursor.execute, PERSIST_QUEUE_DELETE_SCHEDULED)

    def drop(self, guild_id: int):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.cursor.execute, PERSIST_QUEUE_BULK_PLAYED, ({"guild_id": guild_id})
            )

    def enqueued(self, guild_id: int, room_id: int, track: lavalink.Track):
        enqueue_time = track.extras.get("enqueue_time", 0)
        if enqueue_time == 0:
            track.extras["enqueue_time"] = int(time.time())
        track_identifier = track.track_identifier
        track = track_to_json(track)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                self.cursor.execute,
                PERSIST_QUEUE_UPSERT,
                {
                    "guild_id": int(guild_id),
                    "room_id": int(room_id),
                    "played": False,
                    "time": enqueue_time,
                    "track": json.dumps(track),
                    "track_id": track_identifier,
                },
            )
