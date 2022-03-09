from typing import Final

# TODO: https://github.com/Cog-Creators/Red-DiscordBot/pull/3195#issuecomment-567821701
# Thanks a lot Sinbad!

__all__ = [
    # PRAGMA Statements
    "PRAGMA_SET_temp_store",
    "PRAGMA_SET_journal_mode",
    "PRAGMA_SET_read_uncommitted",
    "PRAGMA_FETCH_user_version",
    "PRAGMA_SET_user_version",
    # Data Deletion statement
    "HANDLE_DISCORD_DATA_DELETION_QUERY",
    # Playlist table statements
    "PLAYLIST_CREATE_TABLE",
    "PLAYLIST_DELETE",
    "PLAYLIST_DELETE_SCOPE",
    "PLAYLIST_DELETE_SCHEDULED",
    "PLAYLIST_FETCH_ALL",
    "PLAYLIST_FETCH_ALL_WITH_FILTER",
    "PLAYLIST_FETCH_ALL_CONVERTER",
    "PLAYLIST_FETCH",
    "PLAYLIST_UPSERT",
    "PLAYLIST_CREATE_INDEX",
    # YouTube table statements
    "YOUTUBE_DROP_TABLE",
    "YOUTUBE_CREATE_TABLE",
    "YOUTUBE_CREATE_INDEX",
    "YOUTUBE_UPSERT",
    "YOUTUBE_UPDATE",
    "YOUTUBE_QUERY",
    "YOUTUBE_QUERY_ALL",
    "YOUTUBE_DELETE_OLD_ENTRIES",
    "YOUTUBE_QUERY_LAST_FETCHED_RANDOM",
    # Spotify table statements
    "SPOTIFY_DROP_TABLE",
    "SPOTIFY_CREATE_INDEX",
    "SPOTIFY_CREATE_TABLE",
    "SPOTIFY_UPSERT",
    "SPOTIFY_QUERY",
    "SPOTIFY_QUERY_ALL",
    "SPOTIFY_UPDATE",
    "SPOTIFY_DELETE_OLD_ENTRIES",
    "SPOTIFY_QUERY_LAST_FETCHED_RANDOM",
    # Lavalink table statements
    "LAVALINK_DROP_TABLE",
    "LAVALINK_CREATE_TABLE",
    "LAVALINK_CREATE_INDEX",
    "LAVALINK_UPSERT",
    "LAVALINK_UPDATE",
    "LAVALINK_QUERY",
    "LAVALINK_QUERY_ALL",
    "LAVALINK_QUERY_LAST_FETCHED_RANDOM",
    "LAVALINK_DELETE_OLD_ENTRIES",
    "LAVALINK_FETCH_ALL_ENTRIES_GLOBAL",
    # Persisting Queue statements
    "PERSIST_QUEUE_DROP_TABLE",
    "PERSIST_QUEUE_CREATE_TABLE",
    "PERSIST_QUEUE_CREATE_INDEX",
    "PERSIST_QUEUE_PLAYED",
    "PERSIST_QUEUE_DELETE_SCHEDULED",
    "PERSIST_QUEUE_FETCH_ALL",
    "PERSIST_QUEUE_UPSERT",
    "PERSIST_QUEUE_BULK_PLAYED",
]

# PRAGMA Statements

PRAGMA_SET_temp_store: Final[
    str
] = """
PRAGMA temp_store = 2;
"""
PRAGMA_SET_journal_mode: Final[
    str
] = """
PRAGMA journal_mode = wal;
"""
PRAGMA_SET_read_uncommitted: Final[
    str
] = """
PRAGMA read_uncommitted = 1;
"""
PRAGMA_FETCH_user_version: Final[
    str
] = """
pragma user_version;
"""
PRAGMA_SET_user_version: Final[
    str
] = """
pragma user_version=3;
"""

# Data Deletion
# This is intentionally 2 seperate transactions due to concerns
# Draper had. This should prevent it from being a large issue,
# as this is no different than triggering a bulk deletion now.
HANDLE_DISCORD_DATA_DELETION_QUERY: Final[
    str
] = """
BEGIN TRANSACTION;

UPDATE playlists
SET deleted = true
WHERE scope_id = :user_id ;

UPDATE playlists
SET author_id = 0xde1
WHERE author_id = :user_id ;

COMMIT TRANSACTION;

BEGIN TRANSACTION;

DELETE FROM PLAYLISTS
WHERE deleted=true;

COMMIT TRANSACTION;
"""

# Playlist table statements
PLAYLIST_CREATE_TABLE: Final[
    str
] = """
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
PLAYLIST_DELETE: Final[
    str
] = """
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
PLAYLIST_DELETE_SCOPE: Final[
    str
] = """
DELETE
FROM
    playlists
WHERE
    scope_type = :scope_type ;
"""
PLAYLIST_DELETE_SCHEDULED: Final[
    str
] = """
DELETE
FROM
    playlists
WHERE
    deleted = true;
"""
PLAYLIST_FETCH_ALL: Final[
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
    AND scope_id = :scope_id
    AND deleted = false
    ;
"""
PLAYLIST_FETCH_ALL_WITH_FILTER: Final[
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
        AND scope_id = :scope_id
        AND author_id = :author_id
        AND deleted = false
    )
;
"""
PLAYLIST_FETCH_ALL_CONVERTER: Final[
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
        (
        playlist_id = :playlist_id
        OR
        LOWER(playlist_name) LIKE "%" || COALESCE(LOWER(:playlist_name), "") || "%"
        )
        AND deleted = false
    )
;
"""
PLAYLIST_FETCH: Final[
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
        AND playlist_id = :playlist_id
        AND scope_id = :scope_id
        AND deleted = false
    )
LIMIT 1;
"""
PLAYLIST_UPSERT: Final[
    str
] = """
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
PLAYLIST_CREATE_INDEX: Final[
    str
] = """
CREATE INDEX IF NOT EXISTS name_index ON playlists (
scope_type, playlist_id, playlist_name, scope_id
);
"""

# YouTube table statements
YOUTUBE_DROP_TABLE: Final[
    str
] = """
DROP TABLE IF EXISTS youtube;
"""
YOUTUBE_CREATE_TABLE: Final[
    str
] = """
CREATE TABLE IF NOT EXISTS youtube(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_info TEXT,
    youtube_url TEXT,
    last_updated INTEGER,
    last_fetched INTEGER
);
"""
YOUTUBE_CREATE_INDEX: Final[
    str
] = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_youtube_url
ON youtube (track_info, youtube_url);
"""
YOUTUBE_UPSERT: Final[
    str
] = """INSERT INTO
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
DO UPDATE
  SET
    track_info = excluded.track_info,
    last_updated = excluded.last_updated
"""
YOUTUBE_UPDATE: Final[
    str
] = """
UPDATE youtube
SET last_fetched=:last_fetched
WHERE track_info=:track;
"""
YOUTUBE_QUERY: Final[
    str
] = """
SELECT youtube_url, last_updated
FROM youtube
WHERE
    track_info=:track
    AND last_updated > :maxage
LIMIT 1;
"""
YOUTUBE_QUERY_ALL: Final[
    str
] = """
SELECT youtube_url, last_updated
FROM youtube
"""
YOUTUBE_DELETE_OLD_ENTRIES: Final[
    str
] = """
DELETE FROM youtube
WHERE
    last_updated < :maxage
    ;
"""
YOUTUBE_QUERY_LAST_FETCHED_RANDOM: Final[
    str
] = """
SELECT youtube_url, last_updated
FROM youtube
WHERE
    last_fetched > :day
    AND last_updated > :maxage
LIMIT 100
;
"""

# Spotify table statements
SPOTIFY_DROP_TABLE: Final[
    str
] = """
DROP TABLE IF EXISTS spotify;
"""
SPOTIFY_CREATE_TABLE: Final[
    str
] = """
CREATE TABLE IF NOT EXISTS spotify(
    id TEXT,
    type TEXT,
    uri TEXT,
    track_name TEXT,
    artist_name TEXT,
    song_url TEXT,
    track_info TEXT,
    last_updated INTEGER,
    last_fetched INTEGER
);
"""
SPOTIFY_CREATE_INDEX: Final[
    str
] = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_spotify_uri
ON spotify (id, type, uri);
"""
SPOTIFY_UPSERT: Final[
    str
] = """INSERT INTO
spotify
  (
    id, type, uri, track_name, artist_name,
    song_url, track_info, last_updated, last_fetched
  )
VALUES
  (
    :id, :type, :uri, :track_name, :artist_name,
    :song_url, :track_info, :last_updated, :last_fetched
  )
ON CONFLICT
  (
    id,
    type,
    uri
  )
DO UPDATE
  SET
    track_name = excluded.track_name,
    artist_name = excluded.artist_name,
    song_url = excluded.song_url,
    track_info = excluded.track_info,
    last_updated = excluded.last_updated;
"""
SPOTIFY_UPDATE: Final[
    str
] = """
UPDATE spotify
SET last_fetched=:last_fetched
WHERE uri=:uri;
"""
SPOTIFY_QUERY: Final[
    str
] = """
SELECT track_info, last_updated
FROM spotify
WHERE
    uri=:uri
    AND last_updated > :maxage
LIMIT 1;
"""
SPOTIFY_QUERY_ALL: Final[
    str
] = """
SELECT track_info, last_updated
FROM spotify
"""
SPOTIFY_DELETE_OLD_ENTRIES: Final[
    str
] = """
DELETE FROM spotify
WHERE
    last_updated < :maxage
    ;
"""
SPOTIFY_QUERY_LAST_FETCHED_RANDOM: Final[
    str
] = """
SELECT track_info, last_updated
FROM spotify
WHERE
    last_fetched > :day
    AND last_updated > :maxage
LIMIT 100
;
"""

# Lavalink table statements
LAVALINK_DROP_TABLE: Final[
    str
] = """
DROP TABLE IF EXISTS lavalink ;
"""
LAVALINK_CREATE_TABLE: Final[
    str
] = """
CREATE TABLE IF NOT EXISTS lavalink(
    query TEXT,
    data JSON,
    last_updated INTEGER,
    last_fetched INTEGER

);
"""
LAVALINK_CREATE_INDEX: Final[
    str
] = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_lavalink_query
ON lavalink (query);
"""
LAVALINK_UPSERT: Final[
    str
] = """INSERT INTO
lavalink
  (
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
ON CONFLICT
  (
    query
  )
DO UPDATE
  SET
    data = excluded.data,
    last_updated = excluded.last_updated;
"""
LAVALINK_UPDATE: Final[
    str
] = """
UPDATE lavalink
SET last_fetched=:last_fetched
WHERE query=:query;
"""
LAVALINK_QUERY: Final[
    str
] = """
SELECT data, last_updated
FROM lavalink
WHERE
    query=:query
    AND last_updated > :maxage
LIMIT 1;
"""
LAVALINK_QUERY_ALL: Final[
    str
] = """
SELECT data, last_updated
FROM lavalink
"""
LAVALINK_QUERY_LAST_FETCHED_RANDOM: Final[
    str
] = """
SELECT data, last_updated
FROM lavalink
WHERE
    last_fetched > :day
    AND last_updated > :maxage
LIMIT 100
;
"""
LAVALINK_DELETE_OLD_ENTRIES: Final[
    str
] = """
DELETE FROM lavalink
WHERE
    last_updated < :maxage
    ;
"""
LAVALINK_FETCH_ALL_ENTRIES_GLOBAL: Final[
    str
] = """
SELECT query, data 
FROM lavalink
"""

# Persisting Queue statements
PERSIST_QUEUE_DROP_TABLE: Final[
    str
] = """
DROP TABLE IF EXISTS persist_queue ;
"""
PERSIST_QUEUE_CREATE_TABLE: Final[
    str
] = """
CREATE TABLE IF NOT EXISTS persist_queue(
    guild_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    track JSON NOT NULL,
    played BOOLEAN DEFAULT false,
    track_id TEXT NOT NULL,
    time INTEGER NOT NULL,
    PRIMARY KEY (guild_id, room_id, track_id)
);
"""
PERSIST_QUEUE_CREATE_INDEX: Final[
    str
] = """
CREATE INDEX IF NOT EXISTS track_index ON persist_queue (guild_id, track_id);
"""
PERSIST_QUEUE_PLAYED: Final[
    str
] = """
UPDATE persist_queue
    SET
        played = true
WHERE
    (
        guild_id = :guild_id
        AND track_id = :track_id
    )
;
"""
PERSIST_QUEUE_BULK_PLAYED: Final[
    str
] = """
UPDATE persist_queue
    SET
        played = true
WHERE guild_id = :guild_id
;
"""
PERSIST_QUEUE_DELETE_SCHEDULED: Final[
    str
] = """
DELETE
FROM
    persist_queue
WHERE
    played = true;
"""
PERSIST_QUEUE_FETCH_ALL: Final[
    str
] = """
SELECT
    guild_id, room_id, track
FROM
    persist_queue
WHERE played = false
ORDER BY time ASC;
"""
PERSIST_QUEUE_UPSERT: Final[
    str
] = """
INSERT INTO
    persist_queue (guild_id, room_id, track, played, track_id, time)
VALUES
    (
        :guild_id, :room_id, :track, :played, :track_id, :time
    )
ON CONFLICT (guild_id, room_id, track_id) DO
UPDATE
    SET
        time = excluded.time
"""
