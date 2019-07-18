import base64
import functools
import logging
import os
import time
import weakref
from typing import List

import aiosqlite

from .errors import SpotifyFetchError

log = logging.getLogger("red.audio.cache")


_CREATE_YOUTUBE_TABLE = """
                CREATE TABLE IF NOT EXISTS youtube(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    song_info TEXT,
                    youtube_url TEXT
                )
            """

_CREATE_SPOTIFY_TABLE = """
                        CREATE TABLE IF NOT EXISTS spotify(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            song_url TEXT,
                            track_info TEXT,
                            uri TEXT
                            artist_name TEXT, 
                            track_name TEXT
                        )
                    """

_INSER_YOUTUBE_TABLE = """
        INSERT INTO youtube(song_info, youtube_url) VALUES(?, ?)
    """

_INSER_SPOTIFY_TABLE = """
        INSERT INTO youtube(song_url, track_info, uri, artist_name, track_name) VALUES(?, ?, ?, ?, ?)
    """

_YOUTUBE_TABLE_QUERY = """SELECT youtube_url FROM youtube WHERE song_info='?'"""
_SPOTIFY_TABLE_QUERY = """SELECT track_info FROM spotify WHERE uri=?"""


def method_cache(*lru_args, **lru_kwargs):
    def decorator(func):
        @functools.wraps(func)
        def wrapped_func(self, *args, **kwargs):
            self_weakref = weakref.ref(self)

            @functools.wraps(func)
            @functools.lru_cache(*lru_args, **lru_kwargs)
            def instance_method_cache(*args, **kwargs):
                return func(self_weakref(), *args, **kwargs)

            setattr(self, func.__name__, instance_method_cache)
            return instance_method_cache(*args, **kwargs)

        return wrapped_func

    return decorator


class SpotifyAPI:
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session
        self.spotify_token = None
        self.client_id = None

    @staticmethod
    async def _check_token(token):
        now = int(time.time())
        return token["expires_at"] - now < 60

    @staticmethod
    def _make_token_auth(client_id, client_secret):
        auth_header = base64.b64encode((client_id + ":" + client_secret).encode("ascii"))
        return {"Authorization": "Basic %s" % auth_header.decode("ascii")}

    async def _make_get(self, url, headers=None):
        async with self.session.request("GET", url, headers=headers) as r:
            if r.status != 200:
                log.debug(
                    "Issue making GET request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json()
                    )
                )
            return await r.json()

    async def _make_post(self, url, payload, headers=None):
        async with self.session.post(url, data=payload, headers=headers) as r:
            if r.status != 200:
                log.debug(
                    "Issue making POST request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json()
                    )
                )
            return await r.json()

    async def get_client(self):
        if self.client_id is None:
            self.client_id = (
                await self.bot.db.api_tokens.get_raw("spotify", default={"client_id": ""})
            ).get("client_id")
        return self.client_id

    async def _request_token(self):
        self.client_id = await self.get_client()
        self.client_secret = await self.bot.db.api_tokens.get_raw(
            "spotify", default={"client_secret": ""}
        )
        payload = {"grant_type": "client_credentials"}
        headers = self._make_token_auth(
            self.client_id["client_id"], self.client_secret["client_secret"]
        )
        r = await self._make_post(
            "https://accounts.spotify.com/api/token", payload=payload, headers=headers
        )
        return r

    async def _get_spotify_token(self):
        if self.spotify_token and not await self._check_token(self.spotify_token):
            return self.spotify_token["access_token"]
        token = await self._request_token()
        if token is None:
            log.debug("Requested a token from Spotify, did not end up getting one.")
        try:
            token["expires_at"] = int(time.time()) + token["expires_in"]
        except KeyError:
            return
        self.spotify_token = token
        log.debug("Created a new access token for Spotify: {0}".format(token))
        return self.spotify_token["access_token"]

    async def call(self, url):  # TODO: replace all make_spotify_req in Audio
        token = await self._get_spotify_token()
        return await self._make_get(url, headers={"Authorization": "Bearer {0}".format(token)})


class YouTubeAPI:
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session
        self.api_key = None

    async def get_api_key(self,):
        if self.api_key is None:
            self.api_key = (
                await self.bot.db.api_tokens.get_raw("youtube", default={"api_key": ""})
            ).get("api_key")
        return self.api_key

    async def call(self, query):
        params = {
            "q": query,
            "part": "id",
            "key": await self.get_api_key(),
            "maxResults": 1,
            "type": "video",
        }
        yt_url = "https://www.googleapis.com/youtube/v3/search"
        async with self.session.request("GET", yt_url, params=params) as r:
            if r.status == 400:
                return None
            else:
                search_response = await r.json()
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                return f"https://www.youtube.com/watch?v={search_result['id']['videoId']}"


class MusicCache:
    def __init__(self, bot, session, path):
        self.bot = bot
        self.spotify_api = SpotifyAPI(bot, session)
        self.youtube_api = YouTubeAPI(bot, session)
        self.path = os.path.abspath(str(os.path.join(path, "cache.db")))

    async def initialize(self):
        print(self.path)
        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            await database.execute(_CREATE_YOUTUBE_TABLE)
            await database.execute(_CREATE_SPOTIFY_TABLE)
            await database.commit()
        # await self.con.set_type_codec(
        #     'json',
        #     encoder=json.dumps,
        #     decoder=json.loads,
        #     schema='pg_catalog'
        # )

    async def _insert(self, table, values: tuple):
        if table == "youtube":
            table = _INSER_YOUTUBE_TABLE
        elif table == "spotify":
            table = _INSER_SPOTIFY_TABLE

        async with aiosqlite.connect(self.path, self.bot.loop) as database:
            await database.execute(table, values)
            await database.commit()

    async def _insert_many(self, table, values: List[tuple]):
        if table == "youtube":
            table = _INSER_YOUTUBE_TABLE
        elif table == "spotify":
            table = _INSER_SPOTIFY_TABLE

        async with aiosqlite.connect(self.path, self.bot.loop) as database:
            await database.executemany(table, values)
            await database.commit()

    async def _query(self, stmnt, param):
        async with aiosqlite.connect(self.path, self.bot.loop) as database:
            return await database.fetchone(stmnt, param)

    @staticmethod
    async def _spotify_format_call(stype, key):
        if stype == "album":
            query = "https://api.spotify.com/v1/albums/{0}".format(key)
        elif stype == "track":
            query = "https://api.spotify.com/v1/tracks/{0}".format(key)
        else:
            query = "https://api.spotify.com/v1/playlists/{0}/tracks".format(key)
        return query

    @staticmethod
    def _get_spotify_track_info(track_data):
        artist_name = track_data["artists"][0]["name"]
        track_name = track_data["name"]
        track_info = f"{track_name} {artist_name}"
        song_url = track_data["external_urls"]["spotify"]
        uri = track_data["uri"]

        return artist_name, track_name, track_info, song_url, uri

    async def _spotify_first_time_query(self, query_type, uri):
        youtube_urls = []

        tracks = await self._spotify_fetch_songs(query_type, uri)

        database_entries = []
        for track in tracks:
            artist_name, track_name, track_info, song_url, uri = self._get_spotify_track_info(
                track
            )
            database_entries.append((artist_name, track_name, track_info, song_url, uri))
            val = row = await self._query(_YOUTUBE_TABLE_QUERY, track_info)
            if row:
                val = row.get("youtube_url", None)
            if val is None:
                val = await self.youtube_query(track_info)
            if val:
                youtube_urls.append(val)

        await self._insert_many("spotify", (artist_name, track_name, track_info, song_url, uri))

        return youtube_urls

    async def _youtube_first_time_query(self, track_info):
        track = await self.youtube_api.call(track_info)
        if track:
            await self._insert("youtube", (track_info, track))
        return track

    async def _spotify_fetch_songs(self, query_type, uri, recursive=False):
        if recursive is False:
            call = self._spotify_format_call(query_type, uri)
            results = await self.spotify_api.call(call)
        else:
            results = await self.spotify_api.call(recursive)
        try:
            if results["error"]["status"] == 401:
                raise SpotifyFetchError(
                    (
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    )
                )
        except KeyError:
            pass
        if query_type == "track":
            tracks = [results]
        else:
            try:
                tracks = results["tracks"]["items"]
            except KeyError:
                tracks = results["items"]
        while True:
            try:
                try:
                    tracks.extend(results["tracks"]["items"])
                except KeyError:
                    tracks.extend(results["items"])
            except KeyError:
                raise SpotifyFetchError("This doesn't seem to be a valid Spotify URL or code.")

            try:
                if results["next"] is not None:
                    results = await self._spotify_fetch_songs(query_type, uri, results["next"])
                    continue
                else:
                    break
            except KeyError:
                if results["tracks"]["next"] is not None:
                    results = await self._spotify_fetch_songs(
                        query_type, uri, results["tracks"]["next"]
                    )
                    continue
                else:
                    break
        return tracks

    async def spotify_query(self, query_type, uri):
        val = row = await self._query(_SPOTIFY_TABLE_QUERY, uri)
        if row:
            val = row.get("track_info", None)
        if val is None:
            youtube_urls = self._spotify_first_time_query(query_type, uri)
        else:
            if val is None:
                return None
            youtube_urls = [val]
        return youtube_urls

    async def youtube_query(self, track_info):
        val = row = await self._query(_YOUTUBE_TABLE_QUERY, track_info)
        if row:
            val = row.get("youtube_url", None)
        if val is None:
            youtube_url = self._youtube_first_time_query(track_info)
        else:
            youtube_url = val
        return youtube_url
