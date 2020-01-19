import asyncio
import concurrent
import contextlib
import datetime
import logging
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Dict, List, MutableMapping, Optional, Tuple, Union

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils.dbtools import APSWConnectionWrapper
from .utils import (
    LavalinkCacheFetchForGlobalResult,
    LavalinkCacheFetchResult,
    SpotifyCacheFetchResult,
    YouTubeCacheFetchResult,
)
from ..audio_logging import debug_exc_log
from ..sql_statements import *

log = logging.getLogger("red.cogs.Audio.api.LocalDB")

_SCHEMA_VERSION = 3


class BaseWrapper:
    def __init__(self, bot: Red, config: Config, conn: APSWConnectionWrapper):
        self.bot = bot
        self.config = config
        self.database = conn
        self.statement = SimpleNamespace()
        self.statement.pragma_temp_store = PRAGMA_SET_temp_store
        self.statement.pragma_journal_mode = PRAGMA_SET_journal_mode
        self.statement.pragma_read_uncommitted = PRAGMA_SET_read_uncommitted
        self.statement.set_user_version = PRAGMA_SET_user_version
        self.statement.get_user_version = PRAGMA_FETCH_user_version
        self.fetch_result: dataclass

    async def init(self) -> None:
        """Initialize the local cache"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.database.cursor().execute, self.statement.pragma_temp_store)
            executor.submit(self.database.cursor().execute, self.statement.pragma_journal_mode)
            executor.submit(self.database.cursor().execute, self.statement.pragma_read_uncommitted)
            executor.submit(self.maybe_migrate)
            executor.submit(self.database.cursor().execute, LAVALINK_CREATE_TABLE)
            executor.submit(self.database.cursor().execute, LAVALINK_CREATE_INDEX)
            executor.submit(self.database.cursor().execute, YOUTUBE_CREATE_TABLE)
            executor.submit(self.database.cursor().execute, YOUTUBE_CREATE_INDEX)
            executor.submit(self.database.cursor().execute, SPOTIFY_CREATE_TABLE)
            executor.submit(self.database.cursor().execute, SPOTIFY_CREATE_INDEX)
            await self.clean_up_old_entries()

    def close(self) -> None:
        """Close the connection with the local cache"""
        with contextlib.suppress(Exception):
            self.database.close()

    async def clean_up_old_entries(self) -> None:
        """Delete entries older than x in the local cache tables"""
        max_age = await self.config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values = {"maxage": maxage_int}
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self.database.cursor().execute, LAVALINK_DELETE_OLD_ENTRIES, values)
            executor.submit(self.database.cursor().execute, YOUTUBE_DELETE_OLD_ENTRIES, values)
            executor.submit(self.database.cursor().execute, SPOTIFY_DELETE_OLD_ENTRIES, values)

    def maybe_migrate(self) -> None:
        """Maybe migrate Database schema for the local cache"""
        current_version = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_user_version)]
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
                self.database.cursor().execute,
                self.statement.set_user_version,
                {"version": _SCHEMA_VERSION},
            )

    async def insert(self, values: List[MutableMapping]) -> None:
        """Insert an entry into the local cache"""
        try:
            with self.database.transaction() as transaction:
                transaction.executemany(self.statement.upsert, values)
        except Exception as exc:
            debug_exc_log(log, exc, "Error during table insert")

    async def update(self, values: MutableMapping) -> None:
        """Update an entry of the local cache"""

        try:
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
            values["last_fetched"] = time_now
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(self.database.cursor().execute, self.statement.update, values)
        except Exception as exc:
            debug_exc_log(log, exc, "Error during table update")

    async def _fetch_one(
        self, values: Dict[str, Union[str, int]]
    ) -> Optional[
        Union[LavalinkCacheFetchResult, SpotifyCacheFetchResult, YouTubeCacheFetchResult]
    ]:
        """Get an entry from the local cache"""
        max_age = await self.config.cache_age()
        maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=max_age)
        maxage_int = int(time.mktime(maxage.timetuple()))
        values.update({"maxage": maxage_int})
        row = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_one, values)]
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
        """Get all entries from the local cache"""
        output = []
        row_result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_all, values)]
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
        """Get a random entry from the local cache"""
        row = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [
                    executor.submit(
                        self.database.cursor().execute, self.statement.get_random, values
                    )
                ]
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
    def __init__(self, bot: Red, config: Config, conn: APSWConnectionWrapper):
        super().__init__(bot, config, conn)
        self.statement.upsert = YOUTUBE_UPSERT
        self.statement.update = YOUTUBE_UPDATE
        self.statement.get_one = YOUTUBE_UPDATE
        self.statement.get_all = YOUTUBE_QUERY_ALL
        self.statement.get_random = YOUTUBE_QUERY_LAST_FETCHED_RANDOM
        self.fetch_result = YouTubeCacheFetchResult

    async def fetch_one(
        self, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[str], Optional[datetime.datetime]]:
        """Get an entry from the Youtube table"""
        result = await self._fetch_one(values)
        if not result:
            return None, None
        return result.query, result.updated_on

    async def fetch_all(self, values: Dict[str, Union[str, int]]) -> List[YouTubeCacheFetchResult]:
        """Get all entries from the Youtube table"""
        return await self._fetch_all(values)

    async def fetch_random(self, values: Dict[str, Union[str, int]]) -> Optional[str]:
        """Get a random entry from the Youtube table"""
        result = await self._fetch_random(values)
        if not result:
            return None
        return result.query


class SpotifyTableWrapper(BaseWrapper):
    def __init__(self, bot: Red, config: Config, conn: APSWConnectionWrapper):
        super().__init__(bot, config, conn)
        self.statement.upsert = SPOTIFY_UPSERT
        self.statement.update = SPOTIFY_UPDATE
        self.statement.get_one = SPOTIFY_QUERY
        self.statement.get_all = SPOTIFY_QUERY_ALL
        self.statement.get_random = SPOTIFY_QUERY_LAST_FETCHED_RANDOM
        self.fetch_result = SpotifyCacheFetchResult

    async def fetch_one(
        self, values: Dict[str, Union[str, int]]
    ) -> Tuple[Optional[str], Optional[datetime.datetime]]:
        """Get an entry from the Spotify table"""
        result = await self._fetch_one(values)
        if not result:
            return None, None
        return result.query, result.updated_on

    async def fetch_all(self, values: Dict[str, Union[str, int]]) -> List[SpotifyCacheFetchResult]:
        """Get all entries from the Spotify table"""
        return await self._fetch_all(values)

    async def fetch_random(self, values: Dict[str, Union[str, int]]) -> Optional[str]:
        """Get a random entry from the Spotify table"""
        result = await self._fetch_random(values)
        if not result:
            return None
        return result.query


class LavalinkTableWrapper(BaseWrapper):
    def __init__(self, bot: Red, config: Config, conn: APSWConnectionWrapper):
        super().__init__(bot, config, conn)
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
        """Get an entry from the Lavalink table"""
        result = await self._fetch_one(values)
        if not result:
            return None, None
        return result.query, result.updated_on

    async def fetch_all(
        self, values: Dict[str, Union[str, int]]
    ) -> List[LavalinkCacheFetchResult]:
        """Get all entries from the Lavalink table"""
        return await self._fetch_all(values)

    async def fetch_random(self, values: Dict[str, Union[str, int]]) -> Optional[MutableMapping]:
        """Get a random entry from the Lavalink table"""
        result = await self._fetch_random(values)
        if not result:
            return None
        return result.query

    async def fetch_all_for_global(self):
        """Get all entries from the Lavalink table"""
        output = []
        row_result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            for future in concurrent.futures.as_completed(
                [executor.submit(self.database.cursor().execute, self.statement.get_all_global)]
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
    """Wraps all table apis into 1 object representing the local cache"""

    def __init__(self, bot: Red, config: Config, conn: APSWConnectionWrapper):
        self.bot = bot
        self.config = config
        self.database = conn
        self.lavalink: LavalinkTableWrapper = LavalinkTableWrapper(bot, config, conn)
        self.spotify: SpotifyTableWrapper = SpotifyTableWrapper(bot, config, conn)
        self.youtube: YouTubeTableWrapper = YouTubeTableWrapper(bot, config, conn)
