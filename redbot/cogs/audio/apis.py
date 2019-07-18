import base64
import logging
import os
import time
from typing import List

import aiosqlite

from .errors import SpotifyFetchError

log = logging.getLogger("red.audio.cache")


_DROP_YOUTUBE_TABLE = "DROP TABLE youtube;"

_CREATE_YOUTUBE_TABLE = """
                CREATE TABLE IF NOT EXISTS youtube(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_info TEXT,
                    youtube_url TEXT
                );
            """
_INSERT_YOUTUBE_TABLE = """
        INSERT INTO youtube(track_info, youtube_url) VALUES(?, ?);
    """
_QUERY_YOUTUBE_TABLE = "SELECT youtube_url FROM youtube WHERE track_info=':track';"


_DROP_SPOTIFY_TABLE = "DROP TABLE spotify;"

_CREATE_SPOTIFY_TABLE = """
                        CREATE TABLE IF NOT EXISTS spotify(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            song_url TEXT,
                            track_info TEXT,
                            uri TEXT,
                            artist_name TEXT, 
                            track_name TEXT
                        );
                    """

_INSER_SPOTIFY_TABLE = """
        INSERT INTO spotify(song_url, track_info, uri, artist_name, track_name) VALUES(?, ?, ?, ?, ?);
    """
_QUERY_SPOTIFY_TABLE = "SELECT track_info FROM spotify WHERE uri=':uri';"


class SpotifyAPI:
    def __init__(self, bot, session):
        self.bot = bot
        self.session = session
        self.spotify_token = None
        self.client_id = None
        self.client_secret = None

    @staticmethod
    async def _check_token(token):
        now = int(time.time())
        return token["expires_at"] - now < 60

    @staticmethod
    def _make_token_auth(client_id, client_secret):
        if client_id is None:
            client_id = ""
        if client_secret is None:
            client_secret = ""

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

    async def get_auth(self):
        if self.client_id is None or self.client_secret is None:
            data = await self.bot.db.api_tokens.get_raw(
                "spotify", default={"client_id": None, "client_secret": None}
            )

            self.client_id = data.get("client_id")
            self.client_secret = data.get("client_secret")

    async def _request_token(self):
        await self.get_auth()

        payload = {"grant_type": "client_credentials"}
        headers = self._make_token_auth(self.client_id, self.client_secret)
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

    async def call(self, url):
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
        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            await database.execute(_DROP_SPOTIFY_TABLE)
            await database.execute(_DROP_YOUTUBE_TABLE)
            await database.commit()
            await database.execute(_CREATE_YOUTUBE_TABLE)
            await database.execute(_CREATE_SPOTIFY_TABLE)
            await database.commit()

    async def _insert(self, table, values: tuple):
        if table == "youtube":
            table = _INSERT_YOUTUBE_TABLE
        elif table == "spotify":
            table = _INSER_SPOTIFY_TABLE

        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            await database.execute(table, values)
            await database.commit()

    async def _insert_many(self, table, values: List[tuple]):
        if table == "youtube":
            table = _INSERT_YOUTUBE_TABLE
        elif table == "spotify":
            table = _INSER_SPOTIFY_TABLE

        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            await database.executemany(table, values)
            await database.commit()

    async def _query(self, stmnt, params):
        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            async with database.execute(stmnt, params) as cursor:
                output = await cursor.fetchone()
                print("Querry", output, stmnt)
                return output[0] if output else None

    @staticmethod
    def _spotify_format_call(stype, key):
        if stype == "album":
            query = "https://api.spotify.com/v1/albums/{0}/tracks".format(key)
        elif stype == "track":
            query = "https://api.spotify.com/v1/tracks/{0}".format(key)
        else:
            query = "https://api.spotify.com/v1/playlists/{0}/tracks".format(key)
        return query

    @staticmethod
    def _get_spotify_track_info(track_data):  # This is Erroing
        artist_name = track_data["artists"][0]["name"]
        track_name = track_data["name"]
        track_info = f"{track_name} {artist_name}"
        song_url = track_data["external_urls"]["spotify"]
        uri = track_data["uri"]

        return artist_name, track_name, track_info, song_url, uri

    async def _spotify_first_time_query(self, query_type, uri, skip_youtube=False):
        print("_spotify_first_time_query")
        youtube_urls = []

        tracks = await self._spotify_fetch_tracks(query_type, uri)

        database_entries = []
        for track in tracks:
            artist_name, track_name, track_info, song_url, uri = self._get_spotify_track_info(
                track
            )
            database_entries.append((artist_name, track_name, track_info, song_url, uri))
            if skip_youtube is False:
                val = await self._query(_QUERY_YOUTUBE_TABLE, {"track": track_info})
                if val is None:
                    val = await self.youtube_query(track_info)
                if val:
                    youtube_urls.append(val)
            else:
                youtube_urls.append(track_info)

        await self._insert_many("spotify", database_entries)

        return youtube_urls

    async def _youtube_first_time_query(self, track_info):
        print("_youtube_first_time_query")
        track = await self.youtube_api.call(track_info)
        if track:
            await self._insert("youtube", (track_info, track))
        return track

    async def _spotify_fetch_tracks(self, query_type, uri, recursive=False):
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
            tracks = results["items"]

        while True:
            if query_type == "track":
                break
            try:
                tracks.extend(results["items"])
            except KeyError:
                raise SpotifyFetchError(
                    "This doesn't seem to be a valid Spotify playlist/album URL or code."
                )

            try:
                if results["next"] is not None:
                    results = await self._spotify_fetch_tracks(query_type, uri, results["next"])
                    continue
                else:
                    break
            except KeyError:
                break

        return tracks

    async def spotify_query(self, query_type, uri, skip_youtube=False):
        print("spotify_query")
        val = await self._query(_QUERY_SPOTIFY_TABLE, {"uri": uri})
        youtube_urls = []
        if val is None:
            urls = await self._spotify_first_time_query(query_type, uri, skip_youtube)
            youtube_urls.extend(urls)

        else:
            youtube_urls.append(val)
        return youtube_urls

    async def youtube_query(self, track_info):
        print("youtube_query")
        val = await self._query(_QUERY_YOUTUBE_TABLE, {"track": track_info})
        if val is None:
            youtube_url = await self._youtube_first_time_query(track_info)
        else:
            youtube_url = val
        return youtube_url
