import asyncio
import concurrent
import contextlib
import datetime
import logging
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, List, MutableMapping, Optional, Tuple, Union, Callable

from .utils import (
    LavalinkCacheFetchForGlobalResult,
    LavalinkCacheFetchResult,
    SpotifyCacheFetchResult,
    YouTubeCacheFetchResult,
)
from ..audio_globals import get_config, get_database_connection
from ..audio_logging import debug_exc_log
from ..cog.utils import _SCHEMA_VERSION
from ..sql_statements import *

log = logging.getLogger("red.cogs.Audio.api.LocalDB")


class BaseWrapper:
    def __int__(self):
        self.database = get_database_connection()
        self.config = get_config()
        self.statement = SimpleNamespace()
        self.statement.pragma_temp_store = PRAGMA_SET_temp_store
        self.statement.pragma_journal_mode = PRAGMA_SET_journal_mode
        self.statement.pragma_read_uncommitted = PRAGMA_SET_read_uncommitted
        self.statement.set_user_version = PRAGMA_SET_user_version
        self.statement.get_user_version = PRAGMA_FETCH_user_version
        self.fetch_result: dataclass

    async def init(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                executor.submit(cursor.execute, self.statement.pragma_temp_store)
                executor.submit(cursor.execute, self.statement.pragma_journal_mode)
                executor.submit(cursor.execute, self.statement.pragma_read_uncommitted)
                executor.submit(self.maybe_migrate)

                executor.submit(cursor.execute, LAVALINK_CREATE_TABLE)
                executor.submit(cursor.execute, LAVALINK_CREATE_INDEX)
                executor.submit(cursor.execute, YOUTUBE_CREATE_TABLE)
                executor.submit(cursor.execute, YOUTUBE_CREATE_INDEX)
                executor.submit(cursor.execute, SPOTIFY_CREATE_TABLE)
                executor.submit(cursor.execute, SPOTIFY_CREATE_INDEX)

                await self.clean_up_old_entries()

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.database.close()

    async def clean_up_old_entries(self) -> None:
        max_age = await self.config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values = {"maxage": maxage_int}
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                executor.submit(cursor.execute, LAVALINK_DELETE_OLD_ENTRIES, values)
                executor.submit(cursor.execute, YOUTUBE_DELETE_OLD_ENTRIES, values)
                executor.submit(cursor.execute, SPOTIFY_DELETE_OLD_ENTRIES, values)

    def maybe_migrate(self) -> None:
        current_version = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                for future in concurrent.futures.as_completed(
                    [executor.submit(cursor.execute, self.statement.get_user_version)]
                ):
                    try:
                        row_result = future.result()
                        current_version = row_result.fetchone()
                        break
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed fetch from database")
                if isinstance(current_version, tuple):
                    current_version = current_version[0]
                if current_version == _SCHEMA_VERSION:
                    return
                executor.submit(
                    cursor.execute(self.statement.set_user_version, {"version": _SCHEMA_VERSION})
                )

    async def insert(self, values: List[MutableMapping]) -> None:
        try:
            with self.database.transaction() as transaction:
                transaction.executemany(self.statement.upsert, values)
        except Exception as exc:
            debug_exc_log(log, exc, "Error during table insert")

    async def update(self, values: MutableMapping) -> None:
        try:
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            values["last_fetched"] = time_now
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                with self.database.cursor() as cursor:
                    executor.submit(cursor.execute, self.statement.update, values)
        except Exception as exc:
            debug_exc_log(log, exc, "Error during table update")

    async def _fetch_one(
        self, values: Dict[str, Union[str, int]]
    ) -> Optional[
        Union[LavalinkCacheFetchResult, SpotifyCacheFetchResult, YouTubeCacheFetchResult]
    ]:
        max_age = await self.config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values.update({"maxage": maxage_int})
        row = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                for future in concurrent.futures.as_completed(
                    [executor.submit(cursor.execute, self.statement.get_one, values)]
                ):
                    try:
                        row_result = future.result()
                        row = row_result.fetchone()
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed fetch from database")
        if not row:
            return
        return self.fetch_result(*row)

    async def _fetch_all(
        self, values: Dict[str, Union[str, int]]
    ) -> List[Union[LavalinkCacheFetchResult, SpotifyCacheFetchResult, YouTubeCacheFetchResult]]:
        output = []
        row_result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                for future in concurrent.futures.as_completed(
                    [executor.submit(cursor.execute, self.statement.get_all, values)]
                ):
                    try:
                        row_result = future.result()
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed fetch from database")
        for index, row in enumerate(row_result, start=1):
            if index % 50 == 0:
                await asyncio.sleep(0.01)
            output.append(self.fetch_result(*row))
            await asyncio.sleep(0)
        return output

    async def _fetch_random(
        self, values: Dict[str, Union[str, int]]
    ) -> Optional[
        Union[LavalinkCacheFetchResult, SpotifyCacheFetchResult, YouTubeCacheFetchResult]
    ]:
        row = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                for future in concurrent.futures.as_completed(
                    [executor.submit(cursor.execute, self.statement.get_random, values)]
                ):
                    try:
                        row_result = future.result()
                        row = row_result.fetchone()
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed random fetch from database")
        if not row:
            return
        return self.fetch_result(*row)


class YouTubeTableWrapper(BaseWrapper):
    def __int__(self):
        super().__int__()
        self.statement.upsert = YOUTUBE_UPSERT
        self.statement.update = YOUTUBE_UPDATE
        self.statement.get_one = YOUTUBE_UPDATE
        self.statement.get_all = YOUTUBE_QUERY_ALL
        self.statement.get_random = YOUTUBE_QUERY_LAST_FETCHED_RANDOM
        self.fetch_result = YouTubeCacheFetchResult

    async def fetch_one(
        self, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[str], Optional[datetime.datetime]]:
        result = await self._fetch_one(values)
        if not result:
            return None, None
        return result.query, result.last_updated

    async def fetch_all(self, values: Dict[str, Union[str, int]]) -> List[YouTubeCacheFetchResult]:
        return await self._fetch_all(values)

    async def fetch_random(self, values: Dict[str, Union[str, int]]) -> Optional[str]:
        result = await self._fetch_random(values)
        if not result:
            return None
        return result.query


class SpotifyTableWrapper(BaseWrapper):
    def __int__(self):
        super().__int__()
        self.statement.upsert = SPOTIFY_UPSERT
        self.statement.update = SPOTIFY_UPDATE
        self.statement.get_one = SPOTIFY_QUERY
        self.statement.get_all = SPOTIFY_QUERY_ALL
        self.statement.get_random = SPOTIFY_QUERY_LAST_FETCHED_RANDOM
        self.fetch_result = SpotifyCacheFetchResult

    async def fetch_one(
        self, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[str], Optional[datetime.datetime]]:
        result = await self._fetch_one(values)
        if not result:
            return None, None
        return result.query, result.last_updated

    async def fetch_all(self, values: Dict[str, Union[str, int]]) -> List[SpotifyCacheFetchResult]:
        return await self._fetch_all(values)

    async def fetch_random(self, values: Dict[str, Union[str, int]]) -> Optional[str]:
        result = await self._fetch_random(values)
        if not result:
            return None
        return result.query


class LavalinkTableWrapper(BaseWrapper):
    def __int__(self):
        super().__int__()
        self.statement.upsert = LAVALINK_UPSERT
        self.statement.update = LAVALINK_UPDATE
        self.statement.get_one = LAVALINK_QUERY
        self.statement.get_all = LAVALINK_QUERY_ALL
        self.statement.get_random = LAVALINK_QUERY_LAST_FETCHED_RANDOM
        self.statement.get_all_global = LAVALINK_FETCH_ALL_ENTRIES_GLOBAL
        self.fetch_result = LavalinkCacheFetchResult
        self.fetch_for_global = LavalinkCacheFetchForGlobalResult

    async def fetch_one(
        self, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[MutableMapping], Optional[datetime.datetime]]:
        result = await self._fetch_one(values)
        if not result:
            return None, None
        return result.query, result.last_updated

    async def fetch_all(
        self, values: Dict[str, Union[str, int]]
    ) -> List[LavalinkCacheFetchResult]:
        return await self._fetch_all(values)

    async def fetch_random(self, values: Dict[str, Union[str, int]]) -> Optional[MutableMapping]:
        result = await self._fetch_random(values)
        if not result:
            return None
        return result.query

    async def fetch_all_for_global(self):
        output = []
        row_result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                for future in concurrent.futures.as_completed(
                    [executor.submit(cursor.execute, self.statement.get_all_global)]
                ):
                    try:
                        row_result = future.result()
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed fetch from database")
        for index, row in enumerate(row_result, start=1):
            if index % 50 == 0:
                await asyncio.sleep(0.01)
            output.append(self.fetch_for_global(*row))
            await asyncio.sleep(0)
        return output


class LocalCacheWrapper:
    def __init__(self):
        self.lavalink: LavalinkTableWrapper = LavalinkTableWrapper()
        self.spotify: SpotifyTableWrapper = SpotifyTableWrapper()
        self.youtube: YouTubeTableWrapper = YouTubeTableWrapper()
