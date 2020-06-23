from __future__ import annotations

from typing import Final

__all__ = [
    "DROP_TABLE",
    "CREATE_TABLE",
    "CREATE_INDEX",
    "UPSERT",
    "UPDATE",
    "QUERY",
    "QUERY_ALL",
    "DELETE_OLD_ENTRIES",
    "QUERY_LAST_FETCHED_RANDOM",
]


DROP_TABLE: Final[
    str
] = """
DROP
    TABLE
        IF EXISTS
            youtube
;
"""
CREATE_TABLE: Final[
    str
] = """
CREATE
    TABLE
        IF NOT EXISTS
            youtube(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_info TEXT,
                youtube_url TEXT,
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
            idx_youtube_url
ON
    youtube (
        track_info, youtube_url
        )
;
"""
UPSERT: Final[
    str
] = """-- noinspection SqlResolveForFile

INSERT INTO
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
DO
    UPDATE
        SET
            track_info = excluded.track_info,
            last_updated = excluded.last_updated
;
"""
UPDATE: Final[
    str
] = """
UPDATE
    youtube
SET
    last_fetched=:last_fetched
WHERE
    track_info=:track
;
"""
QUERY: Final[
    str
] = """
SELECT
    youtube_url, last_updated
FROM
    youtube
WHERE
    track_info=:track
    AND
        last_updated > :maxage
LIMIT 1
;
"""
QUERY_ALL: Final[
    str
] = """
SELECT
    youtube_url, last_updated
FROM
    youtube
;
"""
DELETE_OLD_ENTRIES: Final[
    str
] = """
DELETE
FROM
    youtube
WHERE
    last_updated < :maxage
;
"""
QUERY_LAST_FETCHED_RANDOM: Final[
    str
] = """
SELECT
    youtube_url, last_updated
FROM
    youtube
WHERE
    last_fetched > :day
    AND
        last_updated > :maxage
LIMIT 100
;
"""
