from __future__ import annotations

from typing import Final

__all__ = [
    "CREATE_TABLE",
    "DELETE",
    "DELETE_SCOPE",
    "DELETE_SCHEDULED",
    "FETCH_ALL",
    "FETCH_ALL_WITH_FILTER",
    "FETCH_ALL_CONVERTER",
    "FETCH",
    "UPSERT",
    "CREATE_INDEX",
]


CREATE_TABLE: Final[
    str
] = """
CREATE
    TABLE
        IF NOT EXISTS
            playlists (
                scope_type INTEGER NOT NULL,
                playlist_id INTEGER NOT NULL,
                playlist_name TEXT NOT NULL,
                scope_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                deleted BOOLEAN DEFAULT FALSE,
                playlist_url TEXT,
                tracks JSON,
                PRIMARY KEY
                    (
                        playlist_id, scope_id, scope_type
                    )
                )
;
"""
DELETE: Final[
    str
] = """
UPDATE
    playlists
        SET
            deleted = TRUE
WHERE
    (
        scope_type = :scope_type
        AND
            playlist_id = :playlist_id
        AND
            scope_id = :scope_id
    )
;
"""
DELETE_SCOPE: Final[
    str
] = """
DELETE
FROM
    playlists
WHERE
    scope_type = :scope_type
;
"""
DELETE_SCHEDULED: Final[
    str
] = """
DELETE
FROM
    playlists
WHERE
    deleted = TRUE
;
"""
FETCH_ALL: Final[
    str
] = """
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
    AND
        scope_id = :scope_id
    AND
        deleted = FALSE
;
"""
FETCH_ALL_WITH_FILTER: Final[
    str
] = """
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
            scope_id = :scope_id
        AND
            author_id = :author_id
        AND
            deleted = FALSE
    )
;
"""
FETCH_ALL_CONVERTER: Final[
    str
] = """-- noinspection SqlResolveForFile

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
        AND
            deleted = FALSE
    )
;
"""
FETCH: Final[
    str
] = """
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
            playlist_id = :playlist_id
        AND
            scope_id = :scope_id
        AND
            deleted = FALSE
    )
LIMIT 1
;
"""
UPSERT: Final[
    str
] = """ -- noinspection SqlResolve @ any/"excluded"
INSERT
    INTO
        playlists (
            scope_type, playlist_id, playlist_name,
            scope_id, author_id, playlist_url, tracks
            )
VALUES
    (
        :scope_type, :playlist_id, :playlist_name, :scope_id, :author_id, :playlist_url, :tracks
    )
    ON
        CONFLICT
            (
                scope_type, playlist_id, scope_id
            )
        DO
            UPDATE
                SET
                    playlist_name = excluded.playlist_name,
                    playlist_url = excluded.playlist_url,
                    tracks = excluded.tracks
;
"""
CREATE_INDEX: Final[
    str
] = """
CREATE
    INDEX
        IF NOT EXISTS name_index
            ON
                playlists (
                    scope_type, playlist_id, playlist_name, scope_id
                    )
;
"""
