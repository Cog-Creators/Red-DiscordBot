from __future__ import annotations

from typing import Final

__all__ = [
    "DROP_TABLE",
    "CREATE_TABLE",
    "CREATE_INDEX",
    "PLAYED",
    "DELETE_SCHEDULED",
    "FETCH_ALL",
    "UPSERT",
    "BULK_PLAYED",
]


DROP_TABLE: Final[
    str
] = """
DROP
    TABLE
        IF EXISTS
            persist_queue
;
"""
CREATE_TABLE: Final[
    str
] = """
CREATE
    TABLE
        IF NOT EXISTS
            persist_queue(
                guild_id INTEGER NOT NULL,
                room_id INTEGER NOT NULL,
                track JSON NOT NULL,
                played BOOLEAN DEFAULT FALSE,
                track_id TEXT NOT NULL,
                time INTEGER NOT NULL,
                PRIMARY KEY
                    (
                        guild_id, room_id, track_id
                    )
                )
;
"""
CREATE_INDEX: Final[
    str
] = """
CREATE
    INDEX
        IF NOT EXISTS
            track_index
ON
    persist_queue (
        guild_id, track_id
        )
;
"""
PLAYED: Final[
    str
] = """
UPDATE
    persist_queue
        SET
            played = TRUE
WHERE
    (
        guild_id = :guild_id
        AND
            track_id = :track_id
    )
;
"""
BULK_PLAYED: Final[
    str
] = """
UPDATE
    persist_queue
        SET
            played = TRUE
WHERE
    guild_id = :guild_id
;
"""
DELETE_SCHEDULED: Final[
    str
] = """
DELETE
FROM
    persist_queue
WHERE
    played = TRUE
;
"""
FETCH_ALL: Final[
    str
] = """
SELECT
    guild_id, room_id, track
FROM
    persist_queue
WHERE
    played = FALSE
ORDER BY
    time
;
"""
UPSERT: Final[
    str
] = """ -- noinspection SqlResolve
INSERT INTO
    persist_queue (
        guild_id, room_id, track, played, track_id, time
        )
VALUES
    (
        :guild_id, :room_id, :track, :played, :track_id, :time
    )
ON
    CONFLICT (
        guild_id, room_id, track_id
        )
    DO
        UPDATE
            SET
                time = excluded.time
;
"""
