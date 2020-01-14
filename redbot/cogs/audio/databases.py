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

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path

from .errors import InvalidTableError
from .sql_statements import *
from .utils import PlaylistScope

log = logging.getLogger("red.audio.database")

if TYPE_CHECKING:
    database_connection: apsw.Connection
    _bot: Red
    _config: Config
else:
    _config = None
    _bot = None
    database_connection = None


SQLError = apsw.ExecutionCompleteError


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


class PlaylistInterface:
    def __init__(self):
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
        if author_id is not None:
            output = []
            for index, row in enumerate(
                self.cursor.execute(
                    PLAYLIST_FETCH_ALL_WITH_FILTER,
                    ({"scope_type": scope_type, "scope_id": scope_id, "author_id": author_id}),
                ),
                start=1,
            ):
                if index % 50 == 0:
                    await asyncio.sleep(0.01)
                output.append(row)
        else:
            output = []
            for index, row in enumerate(
                self.cursor.execute(
                    PLAYLIST_FETCH_ALL, ({"scope_type": scope_type, "scope_id": scope_id})
                ),
                start=1,
            ):
                if index % 50 == 0:
                    await asyncio.sleep(0.01)
                output.append(row)
        return [PlaylistFetchResult(*row) for row in output] if output else []

    async def fetch_all_converter(
        self, scope: str, playlist_name, playlist_id
    ) -> List[PlaylistFetchResult]:
        scope_type = self.get_scope_type(scope)
        try:
            playlist_id = int(playlist_id)
        except Exception:
            playlist_id = -1

        output = []
        for index, row in enumerate(
            self.cursor.execute(
                PLAYLIST_FETCH_ALL_CONVERTER,
                (
                    {
                        "scope_type": scope_type,
                        "playlist_name": playlist_name,
                        "playlist_id": playlist_id,
                    }
                ),
            ),
            start=1,
        ):
            if index % 50 == 0:
                await asyncio.sleep(0.01)
            output.append(row)
        return [PlaylistFetchResult(*row) for row in output] if output else []

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
