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
    "QUERY_LAST_FETCHED_RANDOM",
    "DELETE_OLD_ENTRIES",
    "FETCH_ALL_ENTRIES_GLOBAL",
]


DROP_TABLE: Final[
    str
] = """
DROP
    TABLE
        IF EXISTS
            lavalink
;
"""
CREATE_TABLE: Final[
    str
] = """
CREATE
    TABLE
        IF NOT EXISTS
            lavalink(
                query TEXT,
                data JSON,
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
            idx_lavalink_query
ON
    lavalink (
        query
        )
;
"""
UPSERT: Final[
    str
] = """ -- noinspection SqlResolve @ any/"excluded"
INSERT
    INTO
        lavalink (
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
ON
    CONFLICT (
        query
        )
    DO
        UPDATE
            SET
                data = excluded.data,
                last_updated = excluded.last_updated
;
"""
UPDATE: Final[
    str
] = """
UPDATE
    lavalink
SET
    last_fetched=:last_fetched
WHERE
    query=:query
;
"""
QUERY: Final[
    str
] = """
SELECT
    data, last_updated
FROM
    lavalink
WHERE
    query=:query
    AND
        last_updated > :maxage
LIMIT 1
;
"""
QUERY_ALL: Final[
    str
] = """
SELECT
    data, last_updated
FROM
    lavalink
;
"""
QUERY_LAST_FETCHED_RANDOM: Final[
    str
] = """
SELECT
    data, last_updated
FROM
    lavalink
WHERE
    last_fetched > :day
    AND
        last_updated > :maxage
LIMIT 100
;
"""
DELETE_OLD_ENTRIES: Final[
    str
] = """
DELETE
    FROM
        lavalink
WHERE
    last_updated < :maxage
;
"""
FETCH_ALL_ENTRIES_GLOBAL: Final[
    str
] = """
SELECT
    query, data
FROM
    lavalink
;
"""
