import asyncio
import base64
import contextlib
import datetime
import json
import logging
import random
import time
from collections import namedtuple
from typing import Callable, List, MutableMapping, Optional, TYPE_CHECKING, Tuple, Union, NoReturn

import aiohttp
import discord
import lavalink
from lavalink.rest_api import LoadResult

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n

from . import audio_dataclasses
from .databases import CacheInterface, SQLError
from .errors import DatabaseError, SpotifyFetchError, YouTubeApiError, TrackEnqueueError
from .playlists import get_playlist
from .utils import CacheLevel, Notifier, is_allowed, queue_duration, track_limit

log = logging.getLogger("red.audio.cache")
_ = Translator("Audio", __file__)

_TOP_100_GLOBALS = "https://www.youtube.com/playlist?list=PL4fGSI1pDJn6puJdseH2Rt9sMvt9E2M4i"
_TOP_100_US = "https://www.youtube.com/playlist?list=PL4fGSI1pDJn5rWitrRWFKdm-ulaFiIyoK"

if TYPE_CHECKING:
    _database: CacheInterface
    _bot: Red
    _config: Config
else:
    _database = None
    _bot = None
    _config = None


def _pass_config_to_apis(config: Config, bot: Red):
    global _database, _config, _bot
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot
    if _database is None:
        _database = CacheInterface()


class SpotifyAPI:
    """Wrapper for the Spotify API."""

    def __init__(self, bot: Red, session: aiohttp.ClientSession):
        self.bot = bot
        self.session = session
        self.spotify_token: Optional[MutableMapping[str, Union[str, int]]] = None
        self.client_id = None
        self.client_secret = None

    @staticmethod
    async def _check_token(token: MutableMapping):
        now = int(time.time())
        return token["expires_at"] - now < 60

    @staticmethod
    def _make_token_auth(
        client_id: Optional[str], client_secret: Optional[str]
    ) -> MutableMapping[str, Union[str, int]]:
        if client_id is None:
            client_id = ""
        if client_secret is None:
            client_secret = ""

        auth_header = base64.b64encode((client_id + ":" + client_secret).encode("ascii"))
        return {"Authorization": "Basic %s" % auth_header.decode("ascii")}

    async def _make_get(
        self, url: str, headers: MutableMapping = None, params: MutableMapping = None
    ) -> MutableMapping[str, str]:
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
        tokens = await self.bot.get_shared_api_tokens("spotify")
        self.client_id = tokens.get("client_id", "")
        self.client_secret = tokens.get("client_secret", "")

    async def _request_token(self) -> MutableMapping[str, Union[str, int]]:
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

    async def post_call(
        self, url: str, payload: MutableMapping, headers: MutableMapping = None
    ) -> MutableMapping[str, Union[str, int]]:
        async with self.session.post(url, data=payload, headers=headers) as r:
            if r.status != 200:
                log.debug(
                    "Issue making POST request to {0}: [{1.status}] {2}".format(
                        url, r, await r.json()
                    )
                )
            return await r.json()

    async def get_call(
        self, url: str, params: MutableMapping
    ) -> MutableMapping[str, Union[str, int]]:
        token = await self._get_spotify_token()
        return await self._make_get(
            url, params=params, headers={"Authorization": "Bearer {0}".format(token)}
        )

    async def get_categories(self) -> List[MutableMapping]:
        url = "https://api.spotify.com/v1/browse/categories"
        params = {}
        result = await self.get_call(url, params=params)
        with contextlib.suppress(KeyError):
            if result["error"]["status"] == 401:
                raise SpotifyFetchError(
                    message=(
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    )
                )
        categories = result.get("categories", {}).get("items", [])
        return [{c["name"]: c["id"]} for c in categories]

    async def get_playlist_from_category(self, category: str):
        url = f"https://api.spotify.com/v1/browse/categories/{category}/playlists"
        params = {}
        result = await self.get_call(url, params=params)
        playlists = result.get("playlists", {}).get("items", [])
        return [
            {
                "name": c["name"],
                "uri": c["uri"],
                "url": c.get("external_urls", {}).get("spotify"),
                "tracks": c.get("tracks", {}).get("total", "Unknown"),
            }
            for c in playlists
        ]


class YouTubeAPI:
    """Wrapper for the YouTube Data API."""

    def __init__(self, bot: Red, session: aiohttp.ClientSession):
        self.bot = bot
        self.session = session
        self.api_key = None

    async def _get_api_key(self,) -> str:
        tokens = await self.bot.get_shared_api_tokens("youtube")
        self.api_key = tokens.get("api_key", "")
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
    """Handles music queries to the Spotify and Youtube Data API.

    Always tries the Cache first.
    """

    def __init__(self, bot: Red, session: aiohttp.ClientSession):
        self.bot = bot
        self.spotify_api: SpotifyAPI = SpotifyAPI(bot, session)
        self.youtube_api: YouTubeAPI = YouTubeAPI(bot, session)
        self._session: aiohttp.ClientSession = session
        self.database = _database

        self._tasks: MutableMapping = {}
        self._lock: asyncio.Lock = asyncio.Lock()
        self.config: Optional[Config] = None

    async def initialize(self, config: Config):
        self.config = config
        await _database.init()

    @staticmethod
    def _spotify_format_call(qtype: str, key: str) -> Tuple[str, MutableMapping]:
        params = {}
        if qtype == "album":
            query = f"https://api.spotify.com/v1/albums/{key}/tracks"
        elif qtype == "track":
            query = f"https://api.spotify.com/v1/tracks/{key}"
        else:
            query = f"https://api.spotify.com/v1/playlists/{key}/tracks"
        return query, params

    @staticmethod
    def _get_spotify_track_info(track_data: MutableMapping) -> Tuple[str, ...]:
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
        time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
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
                    with contextlib.suppress(SQLError):
                        (val, update) = await self.database.fetch_one(
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
            await asyncio.sleep(0)
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
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
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
        params: MutableMapping = None,
        notifier: Optional[Notifier] = None,
    ) -> Union[MutableMapping, List[str]]:

        if recursive is False:
            (call, params) = self._spotify_format_call(query_type, uri)
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
        """Queries the Database then falls back to Spotify and YouTube APIs.

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
            with contextlib.suppress(SQLError):
                (val, update) = await self.database.fetch_one(
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
        has_not_allowed = False
        try:
            current_cache_level = CacheLevel(await self.config.cache_level())
            guild_data = await self.config.guild(ctx.guild).all()

            # now = int(time.time())
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
            time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

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
                    with contextlib.suppress(SQLError):
                        (val, update) = await self.database.fetch_one(
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
                        (result, called_api) = await self.lavalink_query(
                            ctx, player, audio_dataclasses.Query.process_input(val)
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
                            title=_("Player timeout, skipping remaining tracks."),
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
                        title=_("Failing to get tracks, skipping remaining."),
                    )
                    await notifier.update_embed(error_embed)
                    break
                if not track_object:
                    consecutive_fails += 1
                    continue
                consecutive_fails = 0
                single_track = track_object[0]
                if not await is_allowed(
                    ctx.guild,
                    (
                        f"{single_track.title} {single_track.author} {single_track.uri} "
                        f"{str(audio_dataclasses.Query.process_input(single_track))}"
                    ),
                ):
                    has_not_allowed = True
                    log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
                    continue
                track_list.append(single_track)
                if enqueue:
                    if len(player.queue) >= 10000:
                        continue
                    if guild_data["maxlength"] > 0:
                        if track_limit(single_track, guild_data["maxlength"]):
                            enqueued_tracks += 1
                            player.add(ctx.author, single_track)
                            self.bot.dispatch(
                                "red_audio_track_enqueue",
                                player.channel.guild,
                                single_track,
                                ctx.author,
                            )
                    else:
                        enqueued_tracks += 1
                        player.add(ctx.author, single_track)
                        self.bot.dispatch(
                            "red_audio_track_enqueue",
                            player.channel.guild,
                            single_track,
                            ctx.author,
                        )

                    if not player.current:
                        await player.play()
            if len(track_list) == 0:
                if not has_not_allowed:
                    raise SpotifyFetchError(
                        message=_(
                            "Nothing found.\nThe YouTube API key may be invalid "
                            "or you may be rate limited on YouTube's search service.\n"
                            "Check the YouTube API key again and follow the instructions "
                            "at `{prefix}audioset youtubeapi`."
                        ).format(prefix=ctx.prefix)
                    )
            player.maybe_shuffle()
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
        except Exception as e:
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
            with contextlib.suppress(SQLError):
                (val, update) = await self.database.fetch_one(
                    "youtube", "youtube_url", {"track": track_info}
                )
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
        query: audio_dataclasses.Query,
        forced: bool = False,
    ) -> Tuple[LoadResult, bool]:
        """A replacement for :code:`lavalink.Player.load_tracks`. This will try to get a valid
        cached entry first if not found or if in valid it will then call the lavalink API.

        Parameters
        ----------
        ctx: commands.Context
            The context this method is being called under.
        player : lavalink.Player
            The player who's requesting the query.
        query: audio_dataclasses.Query
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
        _raw_query = audio_dataclasses.Query.process_input(query)
        query = str(_raw_query)
        if cache_enabled and not forced and not _raw_query.is_local:
            update = True
            with contextlib.suppress(SQLError):
                (val, update) = await self.database.fetch_one("lavalink", "data", {"query": query})
            if update:
                val = None
            if val and isinstance(val, dict):
                log.debug(f"Querying Local Database for {query}")
                task = ("update", ("lavalink", {"query": query}))
                self.append_task(ctx, *task)
            else:
                val = None
        if val and not forced and isinstance(val, dict):
            data = val
            data["query"] = query
            if data.get("loadType") == "V2_COMPACT":
                data["loadType"] = "V2_COMPAT"
            results = LoadResult(data)
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
            except RuntimeError:
                raise TrackEnqueueError
            if results is None:
                results = LoadResult({"loadType": "LOAD_FAILED", "playlistInfo": {}, "tracks": []})
            if (
                cache_enabled
                and results.load_type
                and not results.has_error
                and not _raw_query.is_local
                and results.tracks
            ):
                with contextlib.suppress(SQLError):
                    time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
                    data = json.dumps(results._raw)
                    if all(
                        k in data for k in ["loadType", "playlistInfo", "isSeekable", "isStream"]
                    ):
                        task = (
                            "insert",
                            (
                                "lavalink",
                                [
                                    {
                                        "query": query,
                                        "data": data,
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
                with contextlib.suppress(Exception):
                    tasks = self._tasks[ctx.message.id]
                    del self._tasks[ctx.message.id]
                    await asyncio.gather(
                        *[self.database.insert(*a) for a in tasks["insert"]],
                        return_exceptions=True,
                    )
                    await asyncio.gather(
                        *[self.database.update(*a) for a in tasks["update"]],
                        return_exceptions=True,
                    )
                log.debug(f"Completed database writes for {lock_id} " f"({lock_author})")

    async def run_all_pending_tasks(self):
        async with self._lock:
            log.debug("Running pending writes to database")
            with contextlib.suppress(Exception):
                tasks = {"update": [], "insert": []}
                for (k, task) in self._tasks.items():
                    for t, args in task.items():
                        tasks[t].append(args)
                self._tasks = {}

                await asyncio.gather(
                    *[self.database.insert(*a) for a in tasks["insert"]], return_exceptions=True
                )
                await asyncio.gather(
                    *[self.database.update(*a) for a in tasks["update"]], return_exceptions=True
                )
            log.debug("Completed pending writes to database have finished")

    def append_task(self, ctx: commands.Context, event: str, task: tuple, _id=None):
        lock_id = _id or ctx.message.id
        if lock_id not in self._tasks:
            self._tasks[lock_id] = {"update": [], "insert": []}
        self._tasks[lock_id][event].append(task)

    async def get_random_from_db(self):
        tracks = []
        try:
            query_data = {}
            date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
            date = int(date.timestamp())
            query_data["day"] = date
            max_age = await self.config.cache_age()
            maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
                days=max_age
            )
            maxage_int = int(time.mktime(maxage.timetuple()))
            query_data["maxage"] = maxage_int

            vals = await self.database.fetch_all("lavalink", "data", query_data)
            recently_played = [r.tracks for r in vals if r if isinstance(tracks, dict)]

            if recently_played:
                track = random.choice(recently_played)
                if track.get("loadType") == "V2_COMPACT":
                    track["loadType"] = "V2_COMPAT"
                results = LoadResult(track)
                tracks = list(results.tracks)
        except Exception:
            tracks = []

        return tracks

    async def autoplay(self, player: lavalink.Player):
        autoplaylist = await self.config.guild(player.channel.guild).autoplaylist()
        current_cache_level = CacheLevel(await self.config.cache_level())
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_cache_level)
        playlist = None
        tracks = None
        if autoplaylist["enabled"]:
            with contextlib.suppress(Exception):
                playlist = await get_playlist(
                    autoplaylist["id"],
                    autoplaylist["scope"],
                    self.bot,
                    player.channel.guild,
                    player.channel.guild.me,
                )
                tracks = playlist.tracks_obj

        if not tracks or not getattr(playlist, "tracks", None):
            if cache_enabled:
                tracks = await self.get_random_from_db()
            if not tracks:
                ctx = namedtuple("Context", "message")
                (results, called_api) = await self.lavalink_query(
                    ctx(player.channel.guild),
                    player,
                    audio_dataclasses.Query.process_input(_TOP_100_US),
                )
                tracks = list(results.tracks)
        if tracks:
            multiple = len(tracks) > 1
            track = tracks[0]

            valid = not multiple
            tries = len(tracks)
            while valid is False and multiple:
                tries -= 1
                if tries <= 0:
                    raise DatabaseError("No valid entry found")
                track = random.choice(tracks)
                query = audio_dataclasses.Query.process_input(track)
                await asyncio.sleep(0.001)
                if not query.valid:
                    continue
                if query.is_local and not query.track.exists():
                    continue
                if not await is_allowed(
                    player.channel.guild,
                    (
                        f"{track.title} {track.author} {track.uri} "
                        f"{str(audio_dataclasses.Query.process_input(track))}"
                    ),
                ):
                    log.debug(
                        "Query is not allowed in "
                        f"{player.channel.guild} ({player.channel.guild.id})"
                    )
                    continue
                valid = True

            track.extras["autoplay"] = True
            player.add(player.channel.guild.me, track)
            self.bot.dispatch(
                "red_audio_track_auto_play", player.channel.guild, track, player.channel.guild.me
            )
            if not player.current:
                await player.play()
