from __future__ import annotations

from typing import Final

__all__ = [
    "DROP_TABLE",
    "CREATE_INDEX",
    "CREATE_TABLE",
    "UPSERT",
    "QUERY",
    "QUERY_ALL",
    "UPDATE",
    "DELETE_OLD_ENTRIES",
    "QUERY_LAST_FETCHED_RANDOM",
]


DROP_TABLE: Final[
    str
] = """
DROP
    TABLE
        IF EXISTS
            spotify
;
"""
CREATE_TABLE: Final[
    str
] = """
CREATE
    TABLE
    IF NOT EXISTS
        spotify(
            id TEXT,
            type TEXT,
            uri TEXT,
            track_name TEXT,
            artist_name TEXT,
            song_url TEXT,
            track_info TEXT,
            last_updated INTEGER,
            last_fetched INTEGER
            )
;
"""
CREATE_INDEX: Final[
    str
] = """
CREATE
    UNIQUE INDEX
        IF NOT EXISTS
            idx_spotify_uri
ON
    spotify (
        id, type, uri
        )
;
"""
UPSERT: Final[
    str
] = """ -- noinspection SqlResolve @ any/"excluded"
INSERT
INTO
    spotify(
        id, type, uri, track_name, artist_name,
        song_url, track_info, last_updated, last_fetched
        )
VALUES
  (
    :id, :type, :uri, :track_name, :artist_name,
    :song_url, :track_info, :last_updated, :last_fetched
  )
ON
    CONFLICT
      (
        id,
        type,
        uri
      )
    DO
        UPDATE
            SET
                track_name = excluded.track_name,
                artist_name = excluded.artist_name,
                song_url = excluded.song_url,
                track_info = excluded.track_info,
                last_updated = excluded.last_updated;
"""
UPDATE: Final[
    str
] = """
UPDATE
    spotify
SET
    last_fetched=:last_fetched
WHERE
    uri=:uri
;
"""
QUERY: Final[
    str
] = """
SELECT
    track_info, last_updated
FROM
    spotify
WHERE
    uri=:uri
    AND
        last_updated > :maxage
LIMIT 1
;
"""
QUERY_ALL: Final[
    str
] = """
SELECT
    track_info, last_updated
FROM
    spotify
;
"""
DELETE_OLD_ENTRIES: Final[
    str
] = """
DELETE
    FROM
        spotify
WHERE
    last_updated < :maxage
;
"""
QUERY_LAST_FETCHED_RANDOM: Final[
    str
] = """
SELECT
    track_info, last_updated
FROM
    spotify
WHERE
    last_fetched > :day
    AND
        last_updated > :maxage
LIMIT 100
;
"""
