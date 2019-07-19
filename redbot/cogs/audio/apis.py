import base64
import logging
import os
import sqlite3
import time
from typing import List, Optional, Dict, Tuple

import aiohttp
import aiosqlite
import discord

from redbot.core.bot import Red
from redbot.core.commands import commands

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

_CREATE_UNIQUE_INDEX_YOUTUBE_TABLE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_youtube_url ON youtube (track_info, youtube_url);"
)

_INSERT_YOUTUBE_TABLE = """
        INSERT OR REPLACE INTO youtube(track_info, youtube_url) VALUES(?, ?);
    """
_QUERY_YOUTUBE_TABLE = "SELECT youtube_url FROM youtube WHERE track_info=:track;"


_DROP_SPOTIFY_TABLE = "DROP TABLE spotify;"

_CREATE_UNIQUE_INDEX_SPOTIFY_TABLE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_spotify_uri ON spotify (id, type, uri);"
)

_CREATE_SPOTIFY_TABLE = """
                        CREATE TABLE IF NOT EXISTS spotify(
                            id TEXT,
                            type TEXT,
                            uri TEXT,
                            track_name TEXT,
                            artist_name TEXT, 
                            song_url TEXT,
                            track_info TEXT
                        );
                    """

_INSERT_SPOTIFY_TABLE = """
        INSERT OR REPLACE INTO spotify(id, type, uri, track_name, artist_name, song_url, track_info) VALUES(?, ?, ?, ?, ?, ?, ?);
    """
_QUERY_SPOTIFY_TABLE = "SELECT track_info FROM spotify WHERE uri=:uri;"


class Notifier:
    def __init__(self, ctx: commands.Context, message: discord.Message, updates: dict, **kwargs):
        self.context = ctx
        self.message = message
        self.updates = updates
        self.color = None

    async def notify_user(self, current: int, total: int, key: str):
        """
        This updates an existing message.
        Based on the message found in :variable:`Notifier.updates` as per the `key` param
        """
        if self.color is None:
            self.color = await self.context.embed_colour()
        embed2 = discord.Embed(
            colour=self.color, title=self.updates.get(key).format(num=current, total=total)
        )
        try:
            await self.message.edit(embed=embed2)
        except discord.errors.NotFound:
            pass


class SpotifyAPI:
    """Wrapper for the Spotify API."""

    def __init__(self, bot: Red, session: aiohttp.ClientSession):
        self.bot = bot
        self.session = session
        self.spotify_token = None
        self.client_id = None
        self.client_secret = None

    @staticmethod
    async def _check_token(token: str):
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

    async def _make_get(self, url: str, headers: dict = None, params: dict = None):
        if params is None:
            params = {}
        async with self.session.request("GET", url, params=params, headers=headers) as r:
            if r.status != 200:
                log.debug(
                    "Issue making GET request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json()
                    )
                )
            return await r.json()

    async def _get_auth(self):
        if self.client_id is None or self.client_secret is None:
            data = await self.bot.db.api_tokens.get_raw(
                "spotify", default={"client_id": None, "client_secret": None}
            )

            self.client_id = data.get("client_id")
            self.client_secret = data.get("client_secret")

    async def _request_token(self):
        await self._get_auth()

        payload = {"grant_type": "client_credentials"}
        headers = self._make_token_auth(self.client_id, self.client_secret)
        r = await self.post_call(
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

    async def post_call(self, url: str, payload: dict, headers: dict = None):
        async with self.session.post(url, data=payload, headers=headers) as r:
            if r.status != 200:
                log.debug(
                    "Issue making POST request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json()
                    )
                )
            return await r.json()

    async def get_call(self, url: str, params: dict):
        token = await self._get_spotify_token()
        return await self._make_get(
            url, params=params, headers={"Authorization": "Bearer {0}".format(token)}
        )


class YouTubeAPI:
    """Wrapper for the YouTube Data API."""

    def __init__(self, bot: Red, session: aiohttp.ClientSession):
        self.bot = bot
        self.session = session
        self.api_key = None

    async def _get_api_key(self,):
        if self.api_key is None:
            self.api_key = (
                await self.bot.db.api_tokens.get_raw("youtube", default={"api_key": ""})
            ).get("api_key")
        return self.api_key

    async def get_call(self, query: str):
        params = {
            "q": query,
            "part": "id",
            "key": await self._get_api_key(),
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
    """
    Handles music queries to the Spotify and Youtube Data API.
    Always tries the Cache first.
    """

    def __init__(self, bot: Red, session: aiohttp.ClientSession, path: str):
        self.bot = bot
        self.spotify_api = SpotifyAPI(bot, session)
        self.youtube_api = YouTubeAPI(bot, session)
        self.path = os.path.abspath(str(os.path.join(path, "cache.db")))

    async def initialize(self):
        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            await database.execute(_CREATE_YOUTUBE_TABLE)
            await database.execute(_CREATE_UNIQUE_INDEX_YOUTUBE_TABLE)
            await database.execute(_CREATE_SPOTIFY_TABLE)
            await database.execute(_CREATE_UNIQUE_INDEX_SPOTIFY_TABLE)
            await database.commit()

    async def _insert(self, table: str, values: tuple) -> None:
        if table == "youtube":
            query = _INSERT_YOUTUBE_TABLE
        elif table == "spotify":
            query = _INSERT_SPOTIFY_TABLE

        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            await database.execute(query, values)
            await database.commit()

    async def _insert_many(self, table: str, values: List[tuple]) -> None:
        if table == "youtube":
            query = _INSERT_YOUTUBE_TABLE
        elif table == "spotify":
            query = _INSERT_SPOTIFY_TABLE

        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            await database.executemany(query, values)
            await database.commit()

    async def _query(self, query: str, params: Dict[str, str]) -> Optional[str]:
        async with aiosqlite.connect(self.path, loop=self.bot.loop) as database:
            async with database.execute(query, params) as cursor:
                output = await cursor.fetchone()
                return output[0] if output else None

    @staticmethod
    def _spotify_format_call(qtype: str, key: str) -> Tuple[str, dict]:
        params = {}
        if qtype == "album":
            query = "https://api.spotify.com/v1/albums/{0}/tracks".format(key)
        elif qtype == "track":
            query = "https://api.spotify.com/v1/tracks/{0}".format(key)
        else:
            query = "https://api.spotify.com/v1/playlists/{0}/tracks".format(key)
            params = {
                "fields": "total, next,items(track(id,type,name,artists,external_urls,uri,is_local))"
            }
        return query, params

    @staticmethod
    def _get_spotify_track_info(track_data: dict) -> Tuple[str, ...]:
        artist_name = track_data["artists"][0]["name"]
        track_name = track_data["name"]
        track_info = f"{track_name} {artist_name}"
        song_url = track_data.get("external_urls", {}).get("spotify")
        uri = track_data["uri"]
        _id = track_data["id"]
        _type = track_data["type"]

        return song_url, track_info, uri, artist_name, track_name, _id, _type

    async def _spotify_first_time_query(
        self, query_type: str, uri: str, skip_youtube: bool = False
    ) -> List[str]:
        youtube_urls = []

        tracks = await self._spotify_fetch_tracks(query_type, uri, params=None)
        total_tracks = len(tracks)
        database_entries = []
        track_count = 0
        for track in tracks:
            song_url, track_info, uri, artist_name, track_name, _id, _type = self._get_spotify_track_info(
                track
            )

            database_entries.append(
                (_id, _type, uri, track_name, artist_name, song_url, track_info)
            )
            if skip_youtube is False:
                val = await self._query(_QUERY_YOUTUBE_TABLE, {"track": track_info})
                if val is None:
                    val = await self._youtube_first_time_query(track_info)
                if val:
                    youtube_urls.append(val)
            else:
                youtube_urls.append(track_info)
            track_count += 1
            if (track_count % 5 == 0) or (track_count == total_tracks):
                if self.notifier:
                    await self.notifier.notify_user(track_count, total_tracks, "youtube")
        try:
            await self._insert_many("spotify", database_entries)
        except sqlite3.OperationalError:
            pass

        return youtube_urls

    async def _youtube_first_time_query(self, track_info: str):
        track_url = await self.youtube_api.get_call(track_info)
        if track_url:
            try:
                await self._insert("youtube", (track_info, track_url))
            except sqlite3.OperationalError:
                pass
        return track_url

    async def _spotify_fetch_tracks(self, query_type: str, uri: str, recursive=False, params=None):

        if recursive is False:
            call, params = self._spotify_format_call(query_type, uri)
            results = await self.spotify_api.get_call(call, params)
        else:
            results = await self.spotify_api.get_call(recursive, params)
        try:
            if results["error"]["status"] == 401 and not recursive:
                raise SpotifyFetchError(
                    (
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    )
                )
            elif recursive:
                return {"next": None}
        except KeyError:
            pass
        if recursive:
            return results
        tracks = []
        track_count = 0
        total_tracks = results.get("total", 1)
        while True:
            new_tracks = 0
            if query_type == "track":
                new_tracks = results
                tracks.append(new_tracks)
            elif query_type == "album":
                tracks_raw = results.get("items", [])
                if tracks_raw:
                    new_tracks = results["items"]
                    tracks.extend(new_tracks)
            else:
                tracks_raw = results.get("items", [])
                if tracks_raw:
                    new_tracks = [k["track"] for k in tracks_raw if k.get("track")]
                    tracks.extend(new_tracks)
            track_count += len(new_tracks)
            if self.notifier:
                await self.notifier.notify_user(track_count, total_tracks, "spotify")

            try:
                if results.get("next") is not None:
                    results = await self._spotify_fetch_tracks(
                        query_type, uri, results["next"], params
                    )
                    continue
                else:
                    break
            except KeyError:
                raise SpotifyFetchError(
                    "This doesn't seem to be a valid Spotify playlist/album URL or code."
                )

        return tracks

    async def spotify_query(
        self, query_type: str, uri: str, skip_youtube: bool = False, notify: Notifier = None
    ):
        self.notifier = notify
        if query_type == "track":
            val = await self._query(_QUERY_SPOTIFY_TABLE, {"uri": f"spotify:track:{uri}"})
        else:
            val = None
        youtube_urls = []
        if val is None:
            urls = await self._spotify_first_time_query(query_type, uri, skip_youtube)
            youtube_urls.extend(urls)

        else:
            youtube_urls.append(val)
        return youtube_urls

    async def youtube_query(self, track_info: str):
        val = await self._query(_QUERY_YOUTUBE_TABLE, {"track": track_info})
        if val is None:
            youtube_url = await self._youtube_first_time_query(track_info)
        else:
            youtube_url = val
        return youtube_url
