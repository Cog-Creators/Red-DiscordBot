import asyncio
import base64
import contextlib
import datetime
import json
import logging
import os
import random
import sqlite3
import time
from typing import List, Optional, Dict, Tuple, Mapping, Union, NoReturn

import aiohttp
from databases import Database
from lavalink.rest_api import LoadResult, Track


from redbot.cogs.audio.utils import Notifier, CacheLevel
from redbot.core.bot import Red
from redbot.core import Config, commands
from redbot.core.i18n import Translator, cog_i18n
from .errors import SpotifyFetchError, InvalidTableError

log = logging.getLogger("red.audio.cache")
_ = Translator("Audio", __file__)


_DROP_YOUTUBE_TABLE = "DROP TABLE youtube;"

_CREATE_YOUTUBE_TABLE = """
                CREATE TABLE IF NOT EXISTS youtube(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_info TEXT,
                    youtube_url TEXT,
                    last_updated TEXT,
                    last_fetched TEXT
                );
            """

_CREATE_UNIQUE_INDEX_YOUTUBE_TABLE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_youtube_url ON youtube (track_info, youtube_url);"
)

_INSERT_YOUTUBE_TABLE = """
        INSERT OR REPLACE INTO 
        youtube(track_info, youtube_url, last_updated, last_fetched) 
        VALUES (:track_info, :track_url, :last_updated, :last_fetched);
    """
_QUERY_YOUTUBE_TABLE = "SELECT * FROM youtube WHERE track_info=:track;"
_UPDATE_YOUTUBE_TABLE = """UPDATE youtube
              SET last_fetched=:last_fetched 
              WHERE track_info=:track;"""

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
                            track_info TEXT,
                            last_updated TEXT,
                            last_fetched TEXT
                        );
                    """

_INSERT_SPOTIFY_TABLE = """
        INSERT OR REPLACE INTO 
        spotify(id, type, uri, track_name, artist_name, song_url, track_info, last_updated, last_fetched) 
        VALUES (:id, :type, :uri, :track_name, :artist_name, :song_url, :track_info, :last_updated, :last_fetched);
    """
_QUERY_SPOTIFY_TABLE = "SELECT * FROM spotify WHERE uri=:uri;"
_UPDATE_SPOTIFY_TABLE = """UPDATE spotify
              SET last_fetched=:last_fetched 
              WHERE uri=:uri;"""

_DROP_LAVALINK_TABLE = "DROP TABLE lavalink;"

_CREATE_LAVALINK_TABLE = """
                CREATE TABLE IF NOT EXISTS lavalink(
                    query TEXT,
                    data BLOB,
                    last_updated TEXT,
                    last_fetched TEXT

                );
            """

_CREATE_UNIQUE_INDEX_LAVALINK_TABLE = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_lavalink_query ON lavalink (query);"
)

_INSERT_LAVALINK_TABLE = """
        INSERT OR REPLACE INTO 
        lavalink(query,  data, last_updated, last_fetched) 
        VALUES (:query, :data, :last_updated, :last_fetched);
    """
_QUERY_LAVALINK_TABLE = "SELECT * FROM lavalink WHERE query=:query;"
_QUERY_LAST_FETCHED_LAVALINK_TABLE = (
    "SELECT * FROM lavalink WHERE last_fetched LIKE :last_fetched;"
)
_UPDATE_LAVALINK_TABLE = """UPDATE lavalink
              SET last_fetched=:last_fetched 
              WHERE query=:query;"""

_PARSER = {
    "youtube": {
        "insert": _INSERT_YOUTUBE_TABLE,
        "youtube_url": {"query": _QUERY_YOUTUBE_TABLE},
        "update": _UPDATE_YOUTUBE_TABLE,
    },
    "spotify": {
        "insert": _INSERT_SPOTIFY_TABLE,
        "track_info": {"query": _QUERY_SPOTIFY_TABLE},
        "update": _UPDATE_SPOTIFY_TABLE,
    },
    "lavalink": {
        "insert": _INSERT_LAVALINK_TABLE,
        "data": {"query": _QUERY_LAVALINK_TABLE, "played": _QUERY_LAST_FETCHED_LAVALINK_TABLE},
        "update": _UPDATE_LAVALINK_TABLE,
    },
}


class SpotifyAPI:
    """Wrapper for the Spotify API."""

    def __init__(self, bot: Red, session: aiohttp.ClientSession):
        self.bot = bot
        self.session = session
        self.spotify_token = None
        self.client_id = None
        self.client_secret = None

    @staticmethod
    async def _check_token(token: dict):
        now = int(time.time())
        return token["expires_at"] - now < 60

    @staticmethod
    def _make_token_auth(client_id: Optional[str], client_secret: Optional[str]) -> dict:
        if client_id is None:
            client_id = ""
        if client_secret is None:
            client_secret = ""

        auth_header = base64.b64encode((client_id + ":" + client_secret).encode("ascii"))
        return {"Authorization": "Basic %s" % auth_header.decode("ascii")}

    async def _make_get(self, url: str, headers: dict = None, params: dict = None) -> dict:
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

    async def _get_auth(self) -> NoReturn:
        if self.client_id is None or self.client_secret is None:
            data = await self.bot.db.api_tokens.get_raw(
                "spotify", default={"client_id": None, "client_secret": None}
            )

            self.client_id = data.get("client_id")
            self.client_secret = data.get("client_secret")

    async def _request_token(self) -> dict:
        await self._get_auth()

        payload = {"grant_type": "client_credentials"}
        headers = self._make_token_auth(self.client_id, self.client_secret)
        r = await self.post_call(
            "https://accounts.spotify.com/api/token", payload=payload, headers=headers
        )
        return r

    async def _get_spotify_token(self) -> Optional[str]:
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

    async def post_call(self, url: str, payload: dict, headers: dict = None) -> dict:
        async with self.session.post(url, data=payload, headers=headers) as r:
            if r.status != 200:
                log.debug(
                    "Issue making POST request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json()
                    )
                )
            return await r.json()

    async def get_call(self, url: str, params: dict) -> dict:
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

    async def _get_api_key(self,) -> Optional[str]:
        if self.api_key is None:
            self.api_key = (
                await self.bot.db.api_tokens.get_raw("youtube", default={"api_key": ""})
            ).get("api_key")
        return self.api_key

    async def get_call(self, query: str) -> Optional[str]:
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


@cog_i18n(_)
class MusicCache:  # So .. Need to see a more efficient way to do the queries
    """
    Handles music queries to the Spotify and Youtube Data API.
    Always tries the Cache first.
    """

    def __init__(self, bot: Red, session: aiohttp.ClientSession, path: str):
        self.bot = bot
        self.spotify_api = SpotifyAPI(bot, session)
        self.youtube_api = YouTubeAPI(bot, session)
        self.database = Database(
            f'sqlite:///{os.path.abspath(str(os.path.join(path, "cache.db")))}'
        )
        self._tasks = {}
        self._lock = asyncio.Lock()

    async def initialize(self, config: Config) -> NoReturn:
        await self.database.connect()
        await self.database.execute(query="PRAGMA TEMP_STORE = 2;")
        await self.database.execute(query=_CREATE_LAVALINK_TABLE)
        await self.database.execute(query=_CREATE_UNIQUE_INDEX_LAVALINK_TABLE)
        await self.database.execute(query=_CREATE_YOUTUBE_TABLE)
        await self.database.execute(query=_CREATE_UNIQUE_INDEX_YOUTUBE_TABLE)
        await self.database.execute(query=_CREATE_SPOTIFY_TABLE)
        await self.database.execute(query=_CREATE_UNIQUE_INDEX_SPOTIFY_TABLE)
        self.config = config

    async def close(self) -> NoReturn:
        await self.database.execute(query="PRAGMA optimize;")
        await self.database.disconnect()

    async def insert(self, table: str, values: List[dict]) -> NoReturn:
        query = _PARSER.get(table, {}).get("insert")
        if query is None:
            raise InvalidTableError(f"{table} is not a valid table in the database.")

        await self.database.execute_many(query=query, values=values)

    async def update(self, table: str, values: Dict[str, str]) -> NoReturn:
        table = _PARSER.get(table, {})
        sql_query = table.get("update")
        time_now = str(datetime.datetime.now(datetime.timezone.utc))
        values["last_fetched"] = time_now
        if not table:
            raise InvalidTableError(f"{table} is not a valid table in the database.")
        await self.database.fetch_one(query=sql_query, values=values)

    async def fetch_one(
        self, table: str, query: str, values: Dict[str, str]
    ) -> Tuple[Optional[str], bool]:
        table = _PARSER.get(table, {})
        sql_query = table.get(query, {}).get("query")
        if not table:
            raise InvalidTableError(f"{table} is not a valid table in the database.")

        row = await self.database.fetch_one(query=sql_query, values=values)
        last_updated = getattr(row, "last_updated", None)
        need_update = (
            (
                datetime.datetime.fromisoformat(last_updated) + datetime.timedelta(days=30)
            )  # TODO: Do not Hard code this ..... Give Owner option to customize
            < datetime.datetime.now(datetime.timezone.utc)
            if last_updated
            else True
        )

        return getattr(row, query, None), need_update  # need_update

        # TODO: Create a task to remove entries from DB that haven't been fetched in x days ... customizable by Owner

    async def fetch_all(self, table: str, query: str, values: Dict[str, str]) -> List[Mapping]:
        table = _PARSER.get(table, {})
        sql_query = table.get(query, {}).get("played")
        if not table:
            raise InvalidTableError(f"{table} is not a valid table in the database.")

        return await self.database.fetch_all(query=sql_query, values=values)

    @staticmethod
    def _spotify_format_call(qtype: str, key: str) -> Tuple[str, dict]:
        params = {}
        if qtype == "album":
            query = "https://api.spotify.com/v1/albums/{0}/tracks".format(key)
        elif qtype == "track":
            query = "https://api.spotify.com/v1/tracks/{0}".format(key)
        else:
            query = "https://api.spotify.com/v1/playlists/{0}/tracks".format(key)
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
        self,
        query_type: str,
        uri: str,
        skip_youtube: bool = False,
        current_cache_level: CacheLevel = CacheLevel.none(),
        ctx: commands.Context = None,
    ) -> List[str]:
        youtube_urls = []

        tracks = await self._spotify_fetch_tracks(query_type, uri, params=None)
        total_tracks = len(tracks)
        database_entries = []
        track_count = 0
        time_now = str(datetime.datetime.now(datetime.timezone.utc))
        youtube_cache = CacheLevel.set_youtube().is_subset(current_cache_level)
        for track in tracks:
            song_url, track_info, uri, artist_name, track_name, _id, _type = self._get_spotify_track_info(
                track
            )

            database_entries.append(
                {
                    "id": _id,
                    "type": _type,
                    "uri": uri,
                    "track_name": track_name,
                    "artist_name": artist_name,
                    "song_url": song_url,
                    "track_info": track_info,
                    "last_updated": time_now,
                    "last_fetched": time_now,
                }
            )
            if skip_youtube is False:
                val = None
                if youtube_cache:
                    val, update = await self.fetch_one(
                        "youtube", "youtube_url", {"track": track_info}
                    )
                    if update:
                        val = None
                if val is None:
                    val = await self._youtube_first_time_query(track_info, current_cache_level=current_cache_level, ctx=ctx)
                if youtube_cache and val:
                    asyncio.create_task(self.update("youtube", {"track": track_info}))

                if val:
                    youtube_urls.append(val)
            else:
                youtube_urls.append(track_info)
            track_count += 1
            if (track_count % 2 == 0) or (track_count == total_tracks):
                if self.notifier:
                    await self.notifier.notify_user(
                        current=track_count, total=total_tracks, key="youtube"
                    )
        if CacheLevel.set_spotify().is_subset(current_cache_level):
            asyncio.create_task(self.insert("spotify", database_entries))
        return youtube_urls

    async def _youtube_first_time_query(
        self,
        track_info: str,
        current_cache_level: CacheLevel = CacheLevel.none(),
        ctx: commands.Context = None,
    ) -> str:
        track_url = await self.youtube_api.get_call(track_info)
        if CacheLevel.set_youtube().is_subset(current_cache_level) and track_url:
            time_now = str(datetime.datetime.now(datetime.timezone.utc))
            asyncio.create_task(
                self.insert(
                    "youtube",
                    [
                        {
                            "track_info": track_info,
                            "track_url": track_url,
                            "last_updated": time_now,
                            "last_fetched": time_now,
                        }
                    ],
                )
            )
        return track_url

    async def _spotify_fetch_tracks(
        self, query_type: str, uri: str, recursive: Union[str, bool] = False, params=None
    ) -> Union[List[str], dict]:

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
        total_tracks = results.get("tracks", results).get("total", 1)
        while True:
            new_tracks = []
            if query_type == "track":
                new_tracks = results
                tracks.append(new_tracks)
            elif query_type == "album":
                tracks_raw = results.get("tracks", results).get("items", [])
                if tracks_raw:
                    new_tracks = tracks_raw
                    tracks.extend(new_tracks)
            else:
                tracks_raw = results.get("tracks", results).get("items", [])
                if tracks_raw:
                    new_tracks = [k["track"] for k in tracks_raw if k.get("track")]
                    tracks.extend(new_tracks)
            track_count += len(new_tracks)
            if self.notifier:
                await self.notifier.notify_user(
                    current=track_count, total=total_tracks, key="spotify"
                )

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
        self,
        query_type: str,
        uri: str,
        skip_youtube: bool = False,
        notify: Notifier = None,
        ctx: commands.Context = None,
    ) -> List[str]:
        self.notifier = notify
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_spotify().is_subset(current_cache_level)
        if query_type == "track" and cache_enabled:
            val, update = await self.fetch_one(
                "spotify", "track_info", {"uri": f"spotify:track:{uri}"}
            )
            if update:
                val = None
        else:
            val = None
        youtube_urls = []
        if val is None:
            urls = await self._spotify_first_time_query(
                query_type, uri, skip_youtube, current_cache_level=current_cache_level, ctx=ctx
            )
            youtube_urls.extend(urls)

        else:
            if query_type == "track" and cache_enabled:
                asyncio.create_task(self.update("spotify", {"uri": f"spotify:track:{uri}"}))
            youtube_urls.append(val)
        return youtube_urls

    async def youtube_query(self, track_info: str, ctx: commands.Context = None) -> str:
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_youtube().is_subset(current_cache_level)
        val = None
        if cache_enabled:
            val, update = await self.fetch_one("youtube", "youtube_url", {"track": track_info})
            if update:
                val = None
        if val is None:
            youtube_url = await self._youtube_first_time_query(
                track_info, current_cache_level=current_cache_level, ctx=ctx
            )
        else:
            if cache_enabled:
                asyncio.create_task(self.update("youtube", {"track": track_info}))
            youtube_url = val
        return youtube_url

    async def lavalink_query(
        self, player, query, forced=False, ctx: commands.Context = None
    ) -> Tuple[List[Track], bool]:
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_cache_level)
        val = None
        if cache_enabled:
            val, update = await self.fetch_one("lavalink", "data", {"query": query})
            if update:
                val = None
            if val:
                asyncio.create_task(self.update("lavalink", {"query": query}))
        if val and not forced:
            results = LoadResult(json.loads(val))
            called_api = False
        else:
            called_api = True
            results = None
            retries = 0
            while results is None:
                with contextlib.suppress(asyncio.TimeoutError, KeyError):
                    results = await player.load_tracks(query)
                retries += 1
                if retries < 3 and results is None:
                    await asyncio.sleep(1)  # TODO: So think of a good way to handle this ...
                if retries == 3 and results is None:
                    return [], called_api
            if cache_enabled and results.load_type and not results.has_error:
                with contextlib.suppress(sqlite3.OperationalError):
                    time_now = str(datetime.datetime.now(datetime.timezone.utc))
                    asyncio.create_task(
                        self.insert(
                            "lavalink",
                            [
                                {
                                    "query": query,
                                    "data": json.dumps(results._raw),
                                    "last_updated": time_now,
                                    "last_fetched": time_now,
                                }
                            ],
                        )
                    )

        return results.tracks, called_api

    async def run_tasks(self, ctx: commands.Context):
        async with self._lock:
            if ctx.message.id in self._tasks:
                tasks = self._tasks[ctx.message.id]
                await asyncio.gather(*tasks, loop=self.bot.loop)
                del self._tasks[ctx.message.id]

    def append_task(self, ctx: commands.Context, task: asyncio.coroutines):
        if ctx.message.id not in self._tasks:
            self._tasks[ctx.message.id] = []
        self._tasks[ctx.message.id].append(task)

    async def play_random(self):  # TODO : Test This
        recently_played = []
        tries = 0
        tracks = []
        while not recently_played:
            date = (
                "%"
                + str(
                    (
                        datetime.datetime.now(datetime.timezone.utc)
                        - datetime.timedelta(days=random.randrange(1, 8))
                    ).date()
                )
                + "%"
            )
            vals = await self.fetch_all("lavalink", "data", {"last_fetched": date})
            recently_played = [r.data for r in vals if r]
            if not recently_played:
                tries += 1
            if tries > 10 and not recently_played: #  Allow owner to customize date range and improve logic
                break

        if recently_played:
            track = random.choice(recently_played)
            results = LoadResult(json.loads(track))
            tracks = results.tracks
        return tracks
