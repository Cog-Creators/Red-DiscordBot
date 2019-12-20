import json
from dataclasses import dataclass, field
from typing import List, Optional

import apsw

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path

from .utils import PlaylistScope

# TODO: https://github.com/Cog-Creators/Red-DiscordBot/pull/3195#issuecomment-567821701
# Thanks a lot Sinbad!

_PRAGMA_UPDATE_temp_store = """
PRAGMA temp_store = 2;
"""
_PRAGMA_UPDATE_journal_mode = """
PRAGMA journal_mode = wal;
"""
_PRAGMA_UPDATE_read_uncommitted = """
PRAGMA read_uncommitted = 1;
"""

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS playlists ( 
    scope_type INTEGER NOT NULL, 
    playlist_id INTEGER NOT NULL, 
    playlist_name TEXT NOT NULL, 
    scope_id INTEGER NOT NULL, 
    author_id INTEGER NOT NULL, 
    deleted BOOLEAN DEFAULT false,
    playlist_url TEXT, 
    tracks JSON, 
    PRIMARY KEY (playlist_id, scope_id, scope_type)
);
"""

_DELETE = """
UPDATE playlists
    SET
        deleted = true
WHERE
    (
        scope_type = :scope_type 
        AND playlist_id = :playlist_id 
        AND scope_id = :scope_id 
    )
;
"""
_DELETE_SCOPE = """
DELETE
FROM
    playlists 
WHERE
    scope_type = :scope_type ;
"""

_DELETE_SCHEDULED = """
DELETE
FROM
    playlists 
WHERE
    deleted = true;
"""

_FETCH_ALL = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    scope_type = :scope_type 
    AND scope_id = :scope_id
    AND deleted = false
    ;
"""

_FETCH_ALL_WITH_FILTER = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    (
        scope_type = :scope_type 
        AND scope_id = :scope_id
        AND author_id = :author_id 
        AND deleted = false
    )
;
"""

_FETCH_ALL_CONVERTER = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    (
        scope_type = :scope_type 
        AND
        (
        playlist_id = :playlist_id
        OR
        LOWER(playlist_name) LIKE "%" || COALESCE(LOWER(:playlist_name), "") || "%"
        )
        AND deleted = false
    )
;
"""

_FETCH = """
SELECT
    playlist_id,
    playlist_name,
    scope_id,
    author_id,
    playlist_url,
    tracks 
FROM
    playlists 
WHERE
    (
        scope_type = :scope_type 
        AND playlist_id = :playlist_id 
        AND scope_id = :scope_id 
        AND deleted = false
    )
"""

_UPSET = """
INSERT INTO
    playlists ( scope_type, playlist_id, playlist_name, scope_id, author_id, playlist_url, tracks ) 
VALUES
    (
        :scope_type, :playlist_id, :playlist_name, :scope_id, :author_id, :playlist_url, :tracks 
    )
    ON CONFLICT (scope_type, playlist_id, scope_id) DO 
    UPDATE
    SET
        playlist_name = excluded.playlist_name, 
        playlist_url = excluded.playlist_url, 
        tracks = excluded.tracks;
"""
_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS name_index ON playlists (scope_type, playlist_id, playlist_name, scope_id);
"""

database_connection: apsw.Connection = None
_config: Config = None
_bot: Red = None


@dataclass
class SQLFetchResult:
    playlist_id: int
    playlist_name: str
    scope_id: int
    author_id: int
    playlist_url: Optional[str] = None
    tracks: List[dict] = field(default_factory=lambda: [])

    def __post_init__(self):
        if isinstance(self.tracks, str):
            self.tracks = json.loads(self.tracks)


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


class PlaylistInterface:
    def __init__(self):
        self.cursor = database_connection.cursor()
        self.cursor.execute(_PRAGMA_UPDATE_temp_store)
        self.cursor.execute(_PRAGMA_UPDATE_journal_mode)
        self.cursor.execute(_PRAGMA_UPDATE_read_uncommitted)
        self.cursor.execute(_CREATE_TABLE)
        self.cursor.execute(_CREATE_INDEX)

    @staticmethod
    def get_scope_type(scope: str) -> int:
        if scope == PlaylistScope.GLOBAL.value:
            table = 1
        elif scope == PlaylistScope.USER.value:
            table = 3
        else:
            table = 2
        return table

    def fetch(self, scope: str, playlist_id: int, scope_id: int) -> SQLFetchResult:
        scope_type = self.get_scope_type(scope)
        row = (
            self.cursor.execute(
                _FETCH,
                ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type}),
            ).fetchone()
            or []
        )

        return SQLFetchResult(*row) if row else None

    def fetch_all(self, scope: str, scope_id: int, author_id=None) -> List[SQLFetchResult]:
        scope_type = self.get_scope_type(scope)
        if author_id is not None:
            output = self.cursor.execute(
                _FETCH_ALL_WITH_FILTER,
                ({"scope_type": scope_type, "scope_id": scope_id, "author_id": author_id}),
            ).fetchall()
        else:
            output = self.cursor.execute(
                _FETCH_ALL, ({"scope_type": scope_type, "scope_id": scope_id})
            ).fetchall()
        return [SQLFetchResult(*row) for row in output] if output else []

    def fetch_all_converter(self, scope: str, playlist_name, playlist_id) -> List[SQLFetchResult]:
        scope_type = self.get_scope_type(scope)
        try:
            playlist_id = int(playlist_id)
        except:
            playlist_id = -1
        output = (
            self.cursor.execute(
                _FETCH_ALL_CONVERTER,
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
        return [SQLFetchResult(*row) for row in output] if output else []

    def delete(self, scope: str, playlist_id: int, scope_id: int):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(
            _DELETE, ({"playlist_id": playlist_id, "scope_id": scope_id, "scope_type": scope_type})
        )

    def delete_scheduled(self):
        return self.cursor.execute(_DELETE_SCHEDULED)

    def drop(self, scope: str):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(_DELETE_SCOPE, ({"scope_type": scope_type}))

    def create_table(self, scope: str):
        scope_type = self.get_scope_type(scope)
        return self.cursor.execute(_CREATE_TABLE, ({"scope_type": scope_type}))

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
            _UPSET,
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
