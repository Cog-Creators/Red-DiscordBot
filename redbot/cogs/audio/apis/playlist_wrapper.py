import asyncio
import concurrent
import json
import logging
from types import SimpleNamespace
from typing import Optional, List, MutableMapping

from redbot.core import Config
from redbot.core.utils.dbtools import APSWConnectionWrapper
from .utils import PlaylistFetchResult
from ..audio_logging import debug_exc_log
from ..sql_statements import (
    PRAGMA_FETCH_user_version,
    PRAGMA_SET_user_version,
    PRAGMA_SET_read_uncommitted,
    PRAGMA_SET_journal_mode,
    PRAGMA_SET_temp_store,
    PLAYLIST_CREATE_TABLE,
    PLAYLIST_CREATE_INDEX,
    PLAYLIST_FETCH_ALL_WITH_FILTER,
    PLAYLIST_FETCH,
    PLAYLIST_FETCH_ALL,
    PLAYLIST_FETCH_ALL_CONVERTER,
    PLAYLIST_UPSERT,
    PLAYLIST_DELETE,
    PLAYLIST_DELETE_SCOPE,
    PLAYLIST_DELETE_SCHEDULED,
)
from ..utils import PlaylistScope

log = logging.getLogger("red.cogs.Audio.api.Playlists")


class PlaylistWrapper:
    def __init__(self, config: Config, conn: APSWConnectionWrapper):
        self.database = conn
        self.config = config
        self.statement = SimpleNamespace()
        self.statement.pragma_temp_store = PRAGMA_SET_temp_store
        self.statement.pragma_journal_mode = PRAGMA_SET_journal_mode
        self.statement.pragma_read_uncommitted = PRAGMA_SET_read_uncommitted
        self.statement.set_user_version = PRAGMA_SET_user_version
        self.statement.get_user_version = PRAGMA_FETCH_user_version
        self.statement.create_table = PLAYLIST_CREATE_TABLE
        self.statement.create_index = PLAYLIST_CREATE_INDEX

        self.statement.upsert = PLAYLIST_UPSERT
        self.statement.delete = PLAYLIST_DELETE
        self.statement.delete_scope = PLAYLIST_DELETE_SCOPE
        self.statement.delete_scheduled = PLAYLIST_DELETE_SCHEDULED

        self.statement.get_one = PLAYLIST_FETCH
        self.statement.get_all = PLAYLIST_FETCH_ALL
        self.statement.get_all_with_filter = PLAYLIST_FETCH_ALL_WITH_FILTER
        self.statement.get_all_converter = PLAYLIST_FETCH_ALL_CONVERTER

    async def init(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                executor.submit(cursor.execute, self.statement.pragma_temp_store)
                executor.submit(cursor.execute, self.statement.pragma_journal_mode)
                executor.submit(cursor.execute, self.statement.pragma_read_uncommitted)
                executor.submit(cursor.execute, self.statement.create_table)
                executor.submit(cursor.execute, self.statement.create_index)

    @staticmethod
    def get_scope_type(scope: str) -> int:
        if scope == PlaylistScope.GLOBAL.value:
            table = 1
        elif scope == PlaylistScope.USER.value:
            table = 3
        else:
            table = 2
        return table

    async def fetch(self, scope: str, playlist_id: int, scope_id: int) -> PlaylistFetchResult:
        scope_type = self.get_scope_type(scope)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                for future in concurrent.futures.as_completed(
                    [
                        executor.submit(
                            cursor.execute,
                            self.statement.get_one,
                            (
                                {
                                    "playlist_id": playlist_id,
                                    "scope_id": scope_id,
                                    "scope_type": scope_type,
                                }
                            ),
                        )
                    ]
                ):
                    try:
                        row_result = future.result()
                    except Exception as exc:
                        debug_exc_log(log, exc, "Failed to completed playlist fetch from database")
            row = row_result.fetchone()
            if row:
                row = PlaylistFetchResult(*row)
        return row

    async def fetch_all(
        self, scope: str, scope_id: int, author_id=None
    ) -> List[PlaylistFetchResult]:
        scope_type = self.get_scope_type(scope)
        output = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:

                if author_id is not None:
                    for future in concurrent.futures.as_completed(
                        [
                            executor.submit(
                                cursor.execute,
                                self.statement.get_all_with_filter,
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
                            debug_exc_log(
                                log, exc, "Failed to completed playlist fetch from database"
                            )
                            return []

                    for index, row in enumerate(row_result, start=1):
                        if index % 50 == 0:
                            await asyncio.sleep(0.01)
                        output.append(PlaylistFetchResult(*row))
                        await asyncio.sleep(0)
                else:
                    for future in concurrent.futures.as_completed(
                        [
                            executor.submit(
                                cursor.execute,
                                self.statement.get_all,
                                ({"scope_type": scope_type, "scope_id": scope_id}),
                            )
                        ]
                    ):
                        try:
                            row_result = future.result()
                        except Exception as exc:
                            debug_exc_log(
                                log, exc, "Failed to completed playlist fetch from database"
                            )
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
            with self.database.cursor() as cursor:
                for future in concurrent.futures.as_completed(
                    [
                        executor.submit(
                            cursor.execute,
                            self.statement.get_all_converter,
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

    async def delete(self, scope: str, playlist_id: int, scope_id: int):
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                executor.submit(
                    cursor.execute,
                    self.statement.delete,
                    ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type}),
                )

    async def delete_scheduled(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                executor.submit(cursor.execute, self.statement.delete_scheduled)

    async def drop(self, scope: str):
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                executor.submit(
                    cursor.execute, self.statement.delete_scope, ({"scope_type": scope_type})
                )

    async def create_table(self, scope: str):
        scope_type = self.get_scope_type(scope)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            with self.database.cursor() as cursor:
                executor.submit(
                    cursor.execute, PLAYLIST_CREATE_TABLE, ({"scope_type": scope_type})
                )

    async def upsert(
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
            with self.database.cursor() as cursor:
                executor.submit(
                    cursor.execute,
                    self.statement.upsert,
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
