# TODO: https://github.com/Cog-Creators/Red-DiscordBot/pull/3195#issuecomment-567821701
# Thanks a lot Sinbad!

__all__ = [
    # PRAGMA Statements
    "PRAGMA_SET_temp_store",
    "PRAGMA_SET_journal_mode",
    "PRAGMA_SET_read_uncommitted",
    "PRAGMA_FETCH_user_version",
    "PRAGMA_SET_user_version",
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
    "YOUTUBE_DELETE_OLD_ENTRIES",
    # Spotify table statements
    "SPOTIFY_DROP_TABLE",
    "SPOTIFY_CREATE_INDEX",
    "SPOTIFY_CREATE_TABLE",
    "SPOTIFY_UPSERT",
    "SPOTIFY_QUERY",
    "SPOTIFY_UPDATE",
    "SPOTIFY_DELETE_OLD_ENTRIES",
    # Lavalink table statements
    "LAVALINK_DROP_TABLE",
    "LAVALINK_CREATE_TABLE",
    "LAVALINK_CREATE_INDEX",
    "LAVALINK_UPSERT",
    "LAVALINK_UPDATE",
    "LAVALINK_QUERY",
    "LAVALINK_QUERY_LAST_FETCHED_RANDOM",
    "LAVALINK_DELETE_OLD_ENTRIES",
    "LAVALINK_FETCH_ALL_ENTRIES_GLOBAL",
]

# PRAGMA Statements
PRAGMA_SET_temp_store = """
PRAGMA temp_store = 2;
"""
PRAGMA_SET_journal_mode = """
PRAGMA journal_mode = wal;
"""
PRAGMA_SET_read_uncommitted = """
PRAGMA read_uncommitted = 1;
"""
PRAGMA_FETCH_user_version = """
pragma user_version;
"""
PRAGMA_SET_user_version = """
pragma user_version=3;
"""

# Playlist table statements
PLAYLIST_CREATE_TABLE = """
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
PLAYLIST_DELETE = """
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
PLAYLIST_DELETE_SCOPE = """
DELETE
FROM
    playlists
WHERE
    scope_type = :scope_type ;
"""
PLAYLIST_DELETE_SCHEDULED = """
DELETE
FROM
    playlists
WHERE
    deleted = true;
"""
PLAYLIST_FETCH_ALL = """
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
PLAYLIST_FETCH_ALL_WITH_FILTER = """
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
PLAYLIST_FETCH_ALL_CONVERTER = """
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
PLAYLIST_FETCH = """
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
PLAYLIST_UPSERT = """
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
PLAYLIST_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS name_index ON playlists (scope_type, playlist_id, playlist_name, scope_id);
"""

# YouTube table statements
YOUTUBE_DROP_TABLE = """
DROP TABLE IF EXISTS youtube;
"""
YOUTUBE_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS youtube(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_info TEXT,
    youtube_url TEXT,
    last_updated INTEGER,
    last_fetched INTEGER
);
"""
YOUTUBE_CREATE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_youtube_url
ON youtube (track_info, youtube_url);
"""
YOUTUBE_UPSERT = """INSERT INTO
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
YOUTUBE_UPDATE = """
UPDATE youtube
SET last_fetched=:last_fetched
WHERE track_info=:track;
"""
YOUTUBE_QUERY = """
SELECT youtube_url, last_updated
FROM youtube
WHERE
    track_info=:track
    AND last_updated > :maxage
LIMIT 1;
"""
YOUTUBE_DELETE_OLD_ENTRIES = """
DELETE FROM youtube
WHERE
    last_updated < :maxage;
"""

# Spotify table statements
SPOTIFY_DROP_TABLE = """
DROP TABLE IF EXISTS spotify;
"""
SPOTIFY_CREATE_TABLE = """
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
SPOTIFY_CREATE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_spotify_uri
ON spotify (id, type, uri);
"""
SPOTIFY_UPSERT = """INSERT INTO
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
SPOTIFY_UPDATE = """
UPDATE spotify
SET last_fetched=:last_fetched
WHERE uri=:uri;
"""
SPOTIFY_QUERY = """
SELECT track_info, last_updated
FROM spotify
WHERE
    uri=:uri
    AND last_updated > :maxage
LIMIT 1;
"""
SPOTIFY_DELETE_OLD_ENTRIES = """
DELETE FROM spotify
WHERE
    last_updated < :maxage;
"""

# Lavalink table statements
LAVALINK_DROP_TABLE = """
DROP TABLE IF EXISTS lavalink ;
"""
LAVALINK_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS lavalink(
    query TEXT,
    data JSON,
    last_updated INTEGER,
    last_fetched INTEGER

);
"""
LAVALINK_CREATE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_lavalink_query
ON lavalink (query);
"""
LAVALINK_UPSERT = """INSERT INTO
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
LAVALINK_UPDATE = """
UPDATE lavalink
SET last_fetched=:last_fetched
WHERE query=:query;
"""
LAVALINK_QUERY = """
SELECT data, last_updated
FROM lavalink
WHERE
    query=:query
    AND last_updated > :maxage
LIMIT 1;
"""
LAVALINK_QUERY_LAST_FETCHED_RANDOM = """
SELECT data
FROM lavalink
WHERE
    last_fetched > :day
    AND last_updated > :maxage
ORDER BY RANDOM()
LIMIT 10
;
"""
LAVALINK_DELETE_OLD_ENTRIES = """
DELETE FROM lavalink
WHERE
    last_updated < :maxage;
"""
LAVALINK_FETCH_ALL_ENTRIES_GLOBAL = """
SELECT query, data 
FROM lavalink
"""
