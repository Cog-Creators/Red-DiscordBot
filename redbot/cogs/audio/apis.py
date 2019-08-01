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
from typing import Callable, Dict, List, Mapping, NoReturn, Optional, Tuple, Union

import aiohttp
import discord
import lavalink
from databases import Database
from lavalink.rest_api import LoadResult

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from . import dataclasses
from .errors import InvalidTableError, SpotifyFetchError, YouTubeApiError
from .playlists import get_playlist
from .utils import CacheLevel, Notifier, dynamic_time, queue_duration, track_limit

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


_TOP_100_GLOBALS = "https://www.youtube.com/playlist?list=PL4fGSI1pDJn6puJdseH2Rt9sMvt9E2M4i"
_TOP_100_US = "https://www.youtube.com/playlist?list=PL4fGSI1pDJn5rWitrRWFKdm-ulaFiIyoK"


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
            if r.status in [400, 404]:
                return None
            elif r.status in [403, 429]:
                if r.reason == "quotaExceeded":
                    raise YouTubeApiError("Your YouTube Data API quota has been reached.")

                return None
            else:
                search_response = await r.json()
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                return f"https://www.youtube.com/watch?v={search_result['id']['videoId']}"


@cog_i18n(_)
class MusicCache:
    """
    Handles music queries to the Spotify and Youtube Data API.
    Always tries the Cache first.
    """

    def __init__(self, bot: Red, session: aiohttp.ClientSession, path: str):
        self.bot = bot
        self.spotify_api: SpotifyAPI = SpotifyAPI(bot, session)
        self.youtube_api: YouTubeAPI = YouTubeAPI(bot, session)
        self._session: aiohttp.ClientSession = session
        self.database: Database = Database(
            f'sqlite:///{os.path.abspath(str(os.path.join(path, "cache.db")))}'
        )
        self._tasks: dict = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self.config: Optional[Config] = None

    async def initialize(self, config: Config) -> NoReturn:
        await self.database.connect()

        await self.database.execute(query="PRAGMA temp_store = 2;")
        await self.database.execute(query="PRAGMA journal_mode = wal;")
        await self.database.execute(query="PRAGMA wal_autocheckpoint;")
        await self.database.execute(query="PRAGMA read_uncommitted = 1;")

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
        # if table == "spotify":
        #     return
        query = _PARSER.get(table, {}).get("insert")
        if query is None:
            raise InvalidTableError(f"{table} is not a valid table in the database.")

        await self.database.execute_many(query=query, values=values)

    async def update(self, table: str, values: Dict[str, str]) -> NoReturn:
        # if table == "spotify":
        #     return
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
                datetime.datetime.fromisoformat(last_updated)
                + datetime.timedelta(days=await self.config.cache_age())
            )
            < datetime.datetime.now(datetime.timezone.utc)
            if last_updated
            else True
        )

        return getattr(row, query, None), need_update if table != "spotify" else True

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
        ctx: commands.Context,
        query_type: str,
        uri: str,
        notifier: Notifier,
        skip_youtube: bool = False,
        current_cache_level: CacheLevel = CacheLevel.none(),
    ) -> List[str]:
        youtube_urls = []

        tracks = await self._spotify_fetch_tracks(query_type, uri, params=None, notifier=notifier)
        total_tracks = len(tracks)
        database_entries = []
        track_count = 0
        time_now = str(datetime.datetime.now(datetime.timezone.utc))
        youtube_cache = CacheLevel.set_youtube().is_subset(current_cache_level)
        for track in tracks:
            if track.get("error", {}).get("message") == "invalid id":
                continue
            (
                song_url,
                track_info,
                uri,
                artist_name,
                track_name,
                _id,
                _type,
            ) = self._get_spotify_track_info(track)

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
                    update = True
                    with contextlib.suppress(sqlite3.Error):
                        val, update = await self.fetch_one(
                            "youtube", "youtube_url", {"track": track_info}
                        )
                    if update:
                        val = None
                if val is None:
                    val = await self._youtube_first_time_query(
                        ctx, track_info, current_cache_level=current_cache_level
                    )
                if youtube_cache and val:
                    task = ("update", ("youtube", {"track": track_info}))
                    self.append_task(ctx, *task)

                if val:
                    youtube_urls.append(val)
            else:
                youtube_urls.append(track_info)
            track_count += 1
            if notifier and ((track_count % 2 == 0) or (track_count == total_tracks)):
                await notifier.notify_user(current=track_count, total=total_tracks, key="youtube")
        if CacheLevel.set_spotify().is_subset(current_cache_level):
            task = ("insert", ("spotify", database_entries))
            self.append_task(ctx, *task)
        return youtube_urls

    async def _youtube_first_time_query(
        self,
        ctx: commands.Context,
        track_info: str,
        current_cache_level: CacheLevel = CacheLevel.none(),
    ) -> str:
        track_url = await self.youtube_api.get_call(track_info)
        if CacheLevel.set_youtube().is_subset(current_cache_level) and track_url:
            time_now = str(datetime.datetime.now(datetime.timezone.utc))
            task = (
                "insert",
                (
                    "youtube",
                    [
                        {
                            "track_info": track_info,
                            "track_url": track_url,
                            "last_updated": time_now,
                            "last_fetched": time_now,
                        }
                    ],
                ),
            )
            self.append_task(ctx, *task)
        return track_url

    async def _spotify_fetch_tracks(
        self,
        query_type: str,
        uri: str,
        recursive: Union[str, bool] = False,
        params=None,
        notifier: Optional[Notifier] = None,
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
            if notifier:
                await notifier.notify_user(current=track_count, total=total_tracks, key="spotify")

            try:
                if results.get("next") is not None:
                    results = await self._spotify_fetch_tracks(
                        query_type, uri, results["next"], params, notifier=notifier
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
        ctx: commands.Context,
        query_type: str,
        uri: str,
        skip_youtube: bool = False,
        notifier: Optional[Notifier] = None,
    ) -> List[str]:
        """
        Queries the Database then falls back to Spotify and YouTube APIs.

        Parameters
        ----------
        ctx: commands.Context
            The context this method is being called under.
        query_type : str
            Type of query to perform (Pl
        uri: str
            Spotify URL ID .
        skip_youtube:bool
            Whether or not to skip YouTube API Calls.
        notifier: Notifier
            A Notifier object to handle the user UI notifications while tracks are loaded.
        Returns
        -------
        List[str]
            List of Youtube URLs.
        """
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_spotify().is_subset(current_cache_level)
        if query_type == "track" and cache_enabled:
            update = True
            with contextlib.suppress(sqlite3.Error):
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
                ctx,
                query_type,
                uri,
                notifier,
                skip_youtube,
                current_cache_level=current_cache_level,
            )
            youtube_urls.extend(urls)
        else:
            if query_type == "track" and cache_enabled:
                task = ("update", ("spotify", {"uri": f"spotify:track:{uri}"}))
                self.append_task(ctx, *task)
            youtube_urls.append(val)
        return youtube_urls

    async def spotify_enqueue(
        self,
        ctx: commands.Context,
        query_type: str,
        uri: str,
        enqueue: bool,
        player: lavalink.Player,
        lock: Callable,
        notifier: Optional[Notifier] = None,
    ) -> List[lavalink.Track]:
        track_list = []
        try:
            current_cache_level = CacheLevel(await self.config.cache_level())
            guild_data = await self.config.guild(ctx.guild).all()

            now = int(time.time())
            enqueued_tracks = 0
            consecutive_fails = 0
            queue_dur = await queue_duration(ctx)
            queue_total_duration = lavalink.utils.format_time(queue_dur)
            before_queue_length = len(player.queue)
            tracks_from_spotify = await self._spotify_fetch_tracks(
                query_type, uri, params=None, notifier=notifier
            )
            total_tracks = len(tracks_from_spotify)
            if total_tracks < 1:
                lock(ctx, False)
                embed3 = discord.Embed(
                    colour=await ctx.embed_colour(),
                    title=_("This doesn't seem to be a supported Spotify URL or code."),
                )
                await notifier.update_embed(embed3)

                return track_list
            database_entries = []
            time_now = str(datetime.datetime.now(datetime.timezone.utc))

            youtube_cache = CacheLevel.set_youtube().is_subset(current_cache_level)
            spotify_cache = CacheLevel.set_spotify().is_subset(current_cache_level)
            for track_count, track in enumerate(tracks_from_spotify):
                (
                    song_url,
                    track_info,
                    uri,
                    artist_name,
                    track_name,
                    _id,
                    _type,
                ) = self._get_spotify_track_info(track)

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
                val = None
                if youtube_cache:
                    update = True
                    with contextlib.suppress(sqlite3.Error):
                        val, update = await self.fetch_one(
                            "youtube", "youtube_url", {"track": track_info}
                        )
                    if update:
                        val = None
                if val is None:
                    val = await self._youtube_first_time_query(
                        ctx, track_info, current_cache_level=current_cache_level
                    )
                if youtube_cache and val:
                    task = ("update", ("youtube", {"track": track_info}))
                    self.append_task(ctx, *task)

                if val:
                    try:
                        result, called_api = await self.lavalink_query(
                            ctx, player, dataclasses.Query.process_input(val)
                        )
                    except (RuntimeError, aiohttp.ServerDisconnectedError):
                        lock(ctx, False)
                        error_embed = discord.Embed(
                            colour=await ctx.embed_colour(),
                            title=_("The connection was reset while loading the playlist."),
                        )
                        await notifier.update_embed(error_embed)
                        break
                    except asyncio.TimeoutError:
                        lock(ctx, False)
                        error_embed = discord.Embed(
                            colour=await ctx.embed_colour(),
                            title=_("Player timedout, skipping remaning tracks."),
                        )
                        await notifier.update_embed(error_embed)
                        break
                    track_object = result.tracks
                else:
                    track_object = []
                if (track_count % 2 == 0) or (track_count == total_tracks):
                    key = "lavalink"
                    seconds = "???"
                    second_key = None
                    if track_count == 2:
                        five_time = int(time.time()) - now
                    if track_count >= 2:
                        remain_tracks = total_tracks - track_count
                        time_remain = (remain_tracks / 2) * five_time
                        if track_count < total_tracks:
                            seconds = dynamic_time(int(time_remain))
                        if track_count == total_tracks:
                            seconds = "0s"
                        second_key = "lavalink_time"
                    await notifier.notify_user(
                        current=track_count,
                        total=total_tracks,
                        key=key,
                        seconds_key=second_key,
                        seconds=seconds,
                    )

                if consecutive_fails >= 10:
                    error_embed = discord.Embed(
                        colour=await ctx.embed_colour(),
                        title=_("Failing to get tracks, skipping remaning."),
                    )
                    await notifier.update_embed(error_embed)
                    break
                if not track_object:
                    consecutive_fails += 1
                    continue
                consecutive_fails = 0
                single_track = track_object[0]
                track_list.append(single_track)
                if enqueue:
                    if guild_data["maxlength"] > 0:
                        if track_limit(single_track, guild_data["maxlength"]):
                            enqueued_tracks += 1
                            player.add(ctx.author, single_track)
                            self.bot.dispatch(
                                "enqueue_track", player.channel.guild, single_track, ctx.author
                            )
                    else:
                        enqueued_tracks += 1
                        player.add(ctx.author, single_track)
                        self.bot.dispatch(
                            "enqueue_track", player.channel.guild, single_track, ctx.author
                        )

                    if not player.current:
                        await player.play()
            if len(track_list) == 0:
                embed3 = discord.Embed(
                    colour=await ctx.embed_colour(),
                    title=_(
                        "Nothing found.\nThe YouTube API key may be invalid "
                        "or you may be rate limited on YouTube's search service.\n"
                        "Check the YouTube API key again and follow the instructions "
                        "at `{prefix}audioset youtubeapi`."
                    ).format(prefix=ctx.prefix),
                )
                await notifier.update_embed(embed3)

            if enqueue and tracks_from_spotify:
                if total_tracks > enqueued_tracks:
                    maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                        bad_tracks=(total_tracks - enqueued_tracks)
                    )
                else:
                    maxlength_msg = ""

                embed = discord.Embed(
                    colour=await ctx.embed_colour(),
                    title=_("Playlist Enqueued"),
                    description=_("Added {num} tracks to the queue.{maxlength_msg}").format(
                        num=enqueued_tracks, maxlength_msg=maxlength_msg
                    ),
                )
                if not guild_data["shuffle"] and queue_dur > 0:
                    embed.set_footer(
                        text=_(
                            "{time} until start of playlist"
                            " playback: starts at #{position} in queue"
                        ).format(time=queue_total_duration, position=before_queue_length + 1)
                    )

                await notifier.update_embed(embed)
            lock(ctx, False)

            if spotify_cache:
                task = ("insert", ("spotify", database_entries))
                self.append_task(ctx, *task)
        except BaseException as e:
            lock(ctx, False)
            raise e
        finally:
            lock(ctx, False)
        return track_list

    async def youtube_query(self, ctx: commands.Context, track_info: str) -> str:
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_youtube().is_subset(current_cache_level)
        val = None
        if cache_enabled:
            update = True
            with contextlib.suppress(sqlite3.Error):
                val, update = await self.fetch_one("youtube", "youtube_url", {"track": track_info})
            if update:
                val = None
        if val is None:
            youtube_url = await self._youtube_first_time_query(
                ctx, track_info, current_cache_level=current_cache_level
            )
        else:
            if cache_enabled:
                task = ("update", ("youtube", {"track": track_info}))
                self.append_task(ctx, *task)
            youtube_url = val
        return youtube_url

    async def lavalink_query(
        self,
        ctx: commands.Context,
        player: lavalink.Player,
        query: dataclasses.Query,
        forced: bool = False,
    ) -> Tuple[LoadResult, bool]:
        """
        A replacement for :code:`lavalink.Player.load_tracks`.
        This will try to get a valid cached entry first if not found or if in valid
        it will then call the lavalink API.

        Parameters
        ----------
        ctx: commands.Context
            The context this method is being called under.
        player : lavalink.Player
            The player who's requesting the query.
        query: dataclasses.Query
            The Query object for the query in question.
        forced:bool
            Whether or not to skip cache and call API first..
        Returns
        -------
        Tuple[lavalink.LoadResult, bool]
            Tuple with the Load result and whether or not the API was called.
        """
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_cache_level)
        val = None
        _raw_query = dataclasses.Query.process_input(query)
        query = str(query)
        if cache_enabled and not forced and not _raw_query.is_local:
            update = True
            with contextlib.suppress(sqlite3.Error):
                val, update = await self.fetch_one("lavalink", "data", {"query": query})
            if update:
                val = None
            if val:
                task = ("update", ("lavalink", {"query": query}))
                self.append_task(ctx, *task)
        if val and not forced:
            results = LoadResult(json.loads(val))
            called_api = False
            if results.has_error:
                # If cached value has an invalid entry make a new call so that it gets updated
                return await self.lavalink_query(ctx, player, _raw_query, forced=True)
        else:
            called_api = True
            results = None
            try:
                results = await player.load_tracks(query)
            except KeyError:
                results = None
            if results is None:
                results = LoadResult({"loadType": "LOAD_FAILED", "playlistInfo": {}, "tracks": []})
            if (
                cache_enabled
                and results.load_type
                and not results.has_error
                and not _raw_query.is_local
            ):
                with contextlib.suppress(sqlite3.Error):
                    time_now = str(datetime.datetime.now(datetime.timezone.utc))
                    task = (
                        "insert",
                        (
                            "lavalink",
                            [
                                {
                                    "query": query,
                                    "data": json.dumps(results._raw),
                                    "last_updated": time_now,
                                    "last_fetched": time_now,
                                }
                            ],
                        ),
                    )
                    self.append_task(ctx, *task)
        return results, called_api

    async def run_tasks(self, ctx: Optional[commands.Context] = None, _id=None):
        lock_id = _id or ctx.message.id
        lock_author = ctx.author if ctx else None
        async with self._lock:
            if lock_id in self._tasks:
                log.debug(f"Running database writes for {lock_id} ({lock_author})")
                with contextlib.suppress(BaseException):
                    tasks = self._tasks[ctx.message.id]
                    del self._tasks[ctx.message.id]
                    await asyncio.gather(
                        *[asyncio.ensure_future(self.insert(*a)) for a in tasks["insert"]],
                        loop=self.bot.loop,
                        return_exceptions=True,
                    )
                    await asyncio.gather(
                        *[asyncio.ensure_future(self.update(*a)) for a in tasks["update"]],
                        loop=self.bot.loop,
                        return_exceptions=True,
                    )
                log.debug(f"Completed database writes for {lock_id} " f"({lock_author})")

    async def run_all_pending_tasks(self):
        async with self._lock:
            log.debug("Running pending writes to database")
            with contextlib.suppress(BaseException):
                tasks = {"update": [], "insert": []}
                for k, task in self._tasks.items():
                    for t, args in task.items():
                        tasks[t].append(args)
                self._tasks = {}

                await asyncio.gather(
                    *[asyncio.ensure_future(self.insert(*a)) for a in tasks["insert"]],
                    loop=self.bot.loop,
                    return_exceptions=True,
                )
                await asyncio.gather(
                    *[asyncio.ensure_future(self.update(*a)) for a in tasks["update"]],
                    loop=self.bot.loop,
                    return_exceptions=True,
                )
            log.debug("Completed pending writes to database have finished")

    def append_task(self, ctx: commands.Context, event: str, task: tuple, _id=None):
        lock_id = _id or ctx.message.id
        if lock_id not in self._tasks:
            self._tasks[lock_id] = {"update": [], "insert": []}
        self._tasks[lock_id][event].append(task)

    async def play_random(self):
        recently_played = []
        tries = 0
        tracks = []
        try:
            # TODO: This is disgusting but it works...
            # Maybe to a full week contain rather and then get a random song from that.
            # Instad of going for a single day that may or may not exist.
            # This is usually only a problem on the first few days of the cache usage
            # Where the change of the date having no entries is larger than
            # The change to have an entry.
            # That is why if this fails 15 times we break and default to a youtube playlist.
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
                if tries > 15 and not recently_played:
                    break

            if recently_played:
                track = random.choice(recently_played)
                results = LoadResult(json.loads(track))
                tracks = results.tracks
        except BaseException:
            tracks = None

        return tracks

    async def autoplay(self, player: lavalink.Player):
        autoplaylist = await self.config.guild(player.channel.guild).autoplaylist()
        playlist = None
        tracks = None
        if autoplaylist["enabled"]:
            try:
                playlist = await get_playlist(
                    autoplaylist["id"],
                    autoplaylist["scope"],
                    self.bot,
                    player.channel.guild,
                    player.channel.guild.me.id,
                )
                tracks = [lavalink.rest_api.Track(data=track) for track in playlist.tracks]
            except BaseException:
                pass

        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_cache_level)
        if playlist is None or not getattr(playlist, "tracks", None):
            if cache_enabled:
                tracks = await self.play_random()
            if not tracks:
                results = await player.load_tracks(_TOP_100_US)
                tracks = results.tracks

        if tracks:
            track = random.choice(tracks)
            player.add(player.channel.guild.me, track)
            self.bot.dispatch(
                "auto_play_track", player.channel.guild, track, player.channel.guild.me
            )
            if not player.current:
                await player.play()
