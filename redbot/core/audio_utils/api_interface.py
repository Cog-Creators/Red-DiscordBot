import aiohttp
import asyncio
import datetime
import time
import random
import logging
import discord
import lavalink
import contextlib
import json

from lavalink.rest_api import LoadResult, LoadType
from typing import ClassVar, Optional, MutableMapping, Union, List, Tuple, Callable

from redbot.core import Config, data_manager
from redbot.core.utils import AsyncIter
from redbot.core.utils.dbtools import APSWConnectionWrapper

from .audio_dataclasses import Query
from .errors import SpotifyFetchError, TrackEnqueueError, YouTubeApiError
from redbot.core.audio_utils.audio_logging import debug_exc_log, IS_DEBUG

from redbot.core.audio_utils.api_utils import get_queue_duration
from redbot.core.audio_utils.utils import CacheLevel
from redbot.core.audio_utils.apis.spotify import SpotifyWrapper
from redbot.core.audio_utils.apis.youtube import YouTubeWrapper
from redbot.core.audio_utils.apis.local_db import LocalCacheWrapper
from redbot.core.audio_utils.apis.persist_queue_wrapper import QueueInterface

log = logging.getLogger("red.core.audio.api_interface")


class AudioAPIInterface:
    def __init__(self, bot, config):
        self._bot = bot
        self._config: Config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._conn: Optional[APSWConnectionWrapper] = None
        self._cog: str = "Audio"
        self._spotify_api: Optional[SpotifyWrapper] = None
        self._youtube_api: Optional[YouTubeWrapper] = None
        self._local_cache_api: Optional[LocalCacheWrapper] = None
        self._global_cache_api: Optional[None] = None
        self._persistent_queue_api: Optional[QueueInterface] = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._is_connected: bool = False
        self._tasks: dict = {}
        self._path = None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def initialize(self) -> None:
        self._session = aiohttp.ClientSession()
        self._conn = APSWConnectionWrapper(
            str(data_manager.cog_data_path(raw_name="Audio") / "Audio.db")
        )

        self._spotify_api: ClassVar[SpotifyWrapper] = SpotifyWrapper(
            self._bot, self._config, self._session, self._cog
        )
        self._youtube_api: ClassVar[YouTubeWrapper] = YouTubeWrapper(
            self._bot, self._config, self._session, self._cog
        )
        self._local_cache_api: ClassVar[LocalCacheWrapper] = LocalCacheWrapper(
            self._bot, self._config, self._conn, self._cog
        )
        # global api?
        self._persistent_queue_api: ClassVar[QueueInterface] = QueueInterface(
            self._bot, self._config, self._conn, self._cog
        )

        await self._local_cache_api.lavalink.init()
        await self._persistent_queue_api.init()
        self._is_connected = True
        if IS_DEBUG:
            log.debug("Database connection established")

    async def close(self) -> None:
        self._local_cache_api.lavalink.close()
        await self._session.close()
        self._is_connected = False

    async def get_random_track_from_db(self) -> Optional[MutableMapping]:
        try:
            query_data = {}
            date = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=7)
            date_timestamp = int(date.timestamp())
            query_data["day"] = date_timestamp
            maxage_conf = await self._config.cache_age()
            maxage = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(
                days=maxage_conf if maxage_conf else 365
            )
            maxage_timestamp = int(time.mktime(maxage.timetuple()))
            query_data["maxage"] = maxage_timestamp
            track = await self._local_cache_api.lavalink.fetch_random(query_data)

            if track:
                if track.get("loadType") == "V2_COMPACT":
                    track["loadType"] == "V2_COMPAT"
                result = LoadResult(track)
                track = random.choice(list(result.tracks))
        except Exception as e:
            if IS_DEBUG:
                log.debug(f"Failed to fetch a random track from db: {e}")
            track = {}

        if not track:
            return None

        return track

    async def _route_tasks(
        self,
        action_type: str = None,
        data: Union[List[MutableMapping], MutableMapping] = None,
    ) -> None:
        """Separate the tasks and run them in the appropriate functions."""

        if not data:
            return
        if action_type == "insert" and isinstance(data, list):
            for table, d in data:
                if table == "lavalink":
                    await self._local_cache_api.lavalink.insert(d)
                elif table == "youtube":
                    await self._local_cache_api.youtube.insert(d)
                elif table == "spotify":
                    await self._local_cache_api.spotify.insert(d)
        elif action_type == "update" and isinstance(data, dict):
            for table, d in data:
                if table == "lavalink":
                    await self._local_cache_api.lavalink.update(data)
                elif table == "youtube":
                    await self._local_cache_api.youtube.update(data)
                elif table == "spotify":
                    await self._local_cache_api.spotify.update(data)
        # elif action_type == "global" and isinstance(data, list): #no global api anymore
        #     await asyncio.gather(*[self.global_cache_api.update_global(**d) for d in data])

    async def run_tasks(self, lock_id: int) -> None:
        async with self._lock:
            if lock_id in self._tasks:
                if IS_DEBUG:
                    log.debug(f"Running database writes for {lock_id}")
                try:
                    tasks = self._tasks[lock_id]
                    tasks = [self._route_tasks(a, tasks[a]) for a in tasks]
                    await asyncio.gather(*tasks, return_exceptions=False)
                    del self._tasks[lock_id]
                except Exception as e:
                    debug_exc_log(log, e, f"Failed database write for {lock_id}")
                else:
                    if IS_DEBUG:
                        log.debug(f"Completed database writes for {lock_id}")

    async def run_all_pending_tasks(self) -> None:
        async with self._lock:
            if IS_DEBUG:
                log.debug("Running pending writes to database")
            try:
                tasks: MutableMapping = {"update": [], "insert": [], "global": []}
                async for k, task in AsyncIter(self._tasks.items()):
                    async for t, args in AsyncIter(task.items()):
                        if t == "insert" and isinstance(args, list):
                            args = args[0]
                        tasks[t].append(args)

                self._tasks = {}
                coro_tasks = [self._route_tasks(a, tasks[a]) for a in tasks]

                await asyncio.gather(*coro_tasks, return_exceptions=False)

            except Exception as e:
                debug_exc_log(log, e, "Failed database writes")
            else:
                if IS_DEBUG:
                    log.debug("Completed pending writes to database")

    def _append_task(self, lock_id: int, event: str, task: Tuple) -> None:
        if lock_id not in self._tasks:
            self._tasks[lock_id] = {"update": [], "insert": [], "global": []}
        self._tasks[lock_id][event].append(task)

    async def fetch_spotify_query(
        self,
        lock_id: int,
        query_type: str,
        uri: str,
        # notifier: Optional[Notifier],
        skip_youtube: bool = False,
        current_cache_level: CacheLevel = CacheLevel.all(),
    ) -> List[str]:
        """Return youtube URLS for the spotify URL provided."""
        youtube_urls = []
        tracks = await self.fetch_from_spotify_api(query_type, uri, params=None)
        database_entries = []
        track_count = 0
        time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        youtube_cache = CacheLevel.set_youtube().is_subset(current_cache_level)
        # global_api = self._cog.global_api_user.get("can_read")
        global_api = None
        async for track in AsyncIter(tracks):
            if isinstance(track, str):
                break
            elif isinstance(track, dict) and track.get("error", {}).get("message") == "invalid id":
                continue
            (
                song_url,
                track_info,
                uri,
                artist_name,
                track_name,
                _id,
                _type,
            ) = await self._spotify_api.get_spotify_track_info(track, lock_id)

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
                    try:
                        (val, last_update) = await self._local_cache_api.youtube.fetch_one(
                            {"track": track_info}
                        )
                    except Exception as exc:
                        debug_exc_log(
                            log, exc, "Failed to fetch %r from YouTube table", track_info
                        )

                if val is None:
                    try:
                        val = await self.fetch_youtube_query(
                            lock_id, track_info, current_cache_level=current_cache_level
                        )
                    except YouTubeApiError as err:
                        val = None
                        youtube_api_error = err.message
                if youtube_cache and val:
                    task = ("update", ("youtube", {"track": track_info}))
                    self._append_task(lock_id, *task)
                if val:
                    youtube_urls.append(val)
            else:
                youtube_urls.append(track_info)
            track_count += 1
            # if notifier is not None and ((track_count % 2 == 0) or (track_count == total_tracks)):
            #     await notifier.notify_user(current=track_count, total=total_tracks, key="youtube")
            # if notifier is not None and (youtube_api_error and not global_api):
            #     error_embed = discord.Embed(
            #         colour=await ctx.embed_colour(),
            #         title=_("Failing to get tracks, skipping remaining."),
            #     )
            #     await notifier.update_embed(error_embed)
            #     break
            # elif notifier is not None and (youtube_api_error and global_api):
            #     continue
        if CacheLevel.set_spotify().is_subset(current_cache_level):
            task = ("insert", ("spotify", database_entries))
            self._append_task(lock_id, *task)
        return youtube_urls

    async def fetch_from_spotify_api(
        self,
        query_type: str,
        uri: str,
        recursive: Union[str, bool] = False,
        params: MutableMapping = None,
    ) -> Union[List[MutableMapping], dict]:
        if not recursive:
            call, params = self._spotify_api.spotify_format_call(query_type, uri)
            results = await self._spotify_api.make_get_call(call, params)
        else:
            if isinstance(recursive, str):
                results = await self._spotify_api.make_get_call(recursive, params)
            else:
                results = {}
        try:
            if results["error"]["status"] == 401 and not recursive:
                raise SpotifyFetchError(
                    "The Spotify Api key or client secret has not been set properly"
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
            new_tracks: List = []
            if query_type == "track":
                new_tracks = results
                tracks.extend(new_tracks)
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

            try:
                if results.get("next"):
                    results = await self.fetch_from_spotify_api(
                        query_type, uri, results["next"], params
                    )
                    continue
                else:
                    break
            except KeyError:
                raise SpotifyFetchError(
                    "This doesn't seem to be a valid Spotify playlist/album URL or code"
                )
        return tracks

    async def spotify_query(
        self, lock_id: int, query_type: str, uri: str, skip_youtube: bool = False
    ):
        cache_level = await self._config.cache_level()
        current_cache_level = CacheLevel(cache_level if cache_level else CacheLevel.all().value)
        cache_enabled = CacheLevel.set_spotify().is_subset(current_cache_level)
        if query_type == "track" and cache_enabled:
            try:
                val, last_update = await self._local_cache_api.spotify.fetch_one(
                    {"uri": f"spotify:track:{uri}"}
                )
            except Exception as exc:
                debug_exc_log(
                    log, exc, "Failed to fetch 'spotify:track:%s' from Spotify table", uri
                )
                val = None
        else:
            val = None
        youtube_urls = []
        if val is None:
            urls = await self.fetch_spotify_query(
                lock_id,
                query_type,
                uri,
                skip_youtube,
                current_cache_level=current_cache_level,
            )
            youtube_urls.extend(urls)
        else:
            if query_type == "track" and cache_enabled:
                task = ("update", ("spotify", {"uri": f"spotify:track:{uri}"}))
                self._append_task(lock_id, *task)
            youtube_urls.append(val)
        return youtube_urls

    async def spotify_enqueue(
        self,
        requester: discord.Member,
        lock_id: int,
        query_type: str,
        uri: str,
        enqueue: bool,
        player: lavalink.Player,
        lock: Callable,
        forced: bool = False,
        query_global: bool = False,
    ):
        globaldb_toggle = False
        global_entry = globaldb_toggle and query_global
        track_list = []
        has_not_allowed = False
        youtube_api_error = None
        skip_youtube_api = False
        try:
            cache_level = await self._config.cache_level()
            current_cache_level = CacheLevel(
                cache_level if cache_level else CacheLevel.all().value
            )
            guild_data = await self._config.guild(requester.guild).all()
            enqueued_tracks = 0
            consecutive_fails = 0
            queue_dur = await get_queue_duration(player)
            before_queue_length = len(player.queue)
            tracks_from_spotify = await self.fetch_from_spotify_api(query_type, uri, params=None)
            total_tracks = len(tracks_from_spotify)

            if total_tracks < 1:
                raise SpotifyFetchError("This doesn't seem to be a supported Spotify URL or code.")

            database_entries = []
            time_now = int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp())
            youtube_cache = CacheLevel.set_youtube().is_subset(current_cache_level)
            spotify_cache = CacheLevel.set_spotify().is_subset(current_cache_level)

            async for track_count, track in AsyncIter(tracks_from_spotify).enumerate(start=1):
                (
                    song_url,
                    track_info,
                    uri,
                    artist_name,
                    track_name,
                    _id,
                    _type,
                ) = await self._spotify_api.get_spotify_track_info(track, lock_id)

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
                llresponse = None
                if youtube_cache:
                    try:
                        (val, last_updated) = await self._local_cache_api.youtube.fetch_one(
                            {"track": track_info}
                        )
                    except Exception as exc:
                        debug_exc_log(
                            log, exc, "Failed to fetch %r from YouTube table", track_info
                        )
                should_query_global = globaldb_toggle and query_global and val is None
                if should_query_global:
                    llresponse = await self._global_cache_api.get_spotify(track_name, artist_name)
                    if llresponse:
                        if llresponse.get("loadType") == "V2_COMPACT":
                            llresponse["loadType"] = "V2_COMPAT"
                        llresponse = LoadResult(llresponse)
                    val = llresponse or None
                if val is None and not skip_youtube_api:
                    try:
                        val = await self.fetch_youtube_query(
                            lock_id, track_info, current_cache_level=current_cache_level
                        )
                    except YouTubeApiError as err:
                        val = None
                        youtube_api_error = err.message
                        skip_youtube_api = True
                if not youtube_api_error:
                    if youtube_cache and val and llresponse is None:
                        task = ("update", ("youtube", {"track": track_info}))
                        self._append_task(lock_id, *task)

                    if isinstance(llresponse, LoadResult):
                        track_object = llresponse.tracks
                    elif val:
                        result = None
                        if should_query_global:
                            llresponse = await self._global_cache_api.get_call(val)
                            if llresponse:
                                if llresponse.get("loadType") == "V2_COMPACT":
                                    llresponse["loadType"] = "V2_COMPAT"
                                llresponse = LoadResult(llresponse)
                            result = llresponse or None
                        if not result:
                            try:
                                (result, called_api) = await self.fetch_track(
                                    lock_id,
                                    player,
                                    Query.process_input(val, self._path),
                                    forced=forced,
                                    should_query_global=not should_query_global,
                                )
                            except (RuntimeError, aiohttp.ServerDisconnectedError):
                                lock(lock_id, False)
                                if IS_DEBUG:
                                    log.debug("Connection reset while loading playlist")
                                break
                            except asyncio.TimeoutError:
                                lock(lock_id, False)
                                if IS_DEBUG:
                                    log.debug("Player timeout. Skipping remaining...")
                                break
                        track_object = result.tracks
                    else:
                        track_object = []
                else:
                    track_object = []

                if (youtube_api_error and not global_entry) or consecutive_fails >= (
                    20 if global_entry else 10
                ):
                    if IS_DEBUG:
                        log.debug("Failing to get tracks. Skipping remaining...")
                    if youtube_api_error:
                        lock(lock_id, False)
                        raise SpotifyFetchError(message=youtube_api_error)
                    break
                if not track_object:
                    consecutive_fails += 1
                    continue
                consecutive_fails = 0
                single_track = track_object[0]
                # query = Query.process_input(single_track, self._path)
                # if not await self.cog.is_query_allowed(
                #     self._config,
                #     ctx,
                #     f"{single_track.title} {single_track.author} {single_track.uri} {query}",
                #     query_obj=query,
                # ):
                #     has_not_allowed = True
                #     if IS_DEBUG:
                #         log.debug("Query is not allowed in %r (%d)", requester.guild.name, requester.guild.id)
                #     continue
                track_list.append(single_track)
                if enqueue:
                    if len(player.queue) >= 10000:
                        continue
                    if guild_data["maxlength"] > 0:
                        # if self.cog.is_track_length_allowed(single_track, guild_data["maxlength"]):
                        enqueued_tracks += 1
                        single_track.extras.update(
                            {
                                "enqueue_time": int(time.time()),
                                "vc": player.channel.id,
                                "requester": requester.id,
                            }
                        )
                        player.add(requester, single_track)
                        self._bot.dispatch(
                            "red_audio_track_enqueue",
                            player.guild,
                            single_track,
                            requester,
                        )
                    else:
                        enqueued_tracks += 1
                        single_track.extras.update(
                            {
                                "enqueue_time": int(time.time()),
                                "vc": player.channel.id,
                                "requester": requester,
                            }
                        )
                        player.add(requester, single_track)
                        self._bot.dispatch(
                            "red_audio_track_enqueue",
                            player.guild,
                            single_track,
                            requester,
                        )

                    if not player.current:
                        await player.play()
            if enqueue and tracks_from_spotify:
                if total_tracks > enqueued_tracks:
                    maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                        bad_tracks=(total_tracks - enqueued_tracks)
                    )
                else:
                    maxlength_msg = ""

                if IS_DEBUG:
                    log.debug(f"Added {enqueued_tracks} tracks to the queue. {maxlength_msg}")

                # if not guild_data["shuffle"] and queue_dur > 0:
                #     embed.set_footer(
                #         text=_(
                #             "{time} until start of playlist"
                #             " playback: starts at #{position} in queue"
                #         ).format(time=queue_total_duration, position=before_queue_length + 1)
                #     )

            lock(lock_id, False)
            if not track_list and not has_not_allowed:
                raise SpotifyFetchError(
                    message="Nothing found.\nThe YouTube API key may be invalid "
                    "or you may be rate limited on YouTube's search service.\n"
                    "Check the YouTube API key again and follow the instructions "
                    "at `{prefix}audioset youtubeapi`."
                )
            player.maybe_shuffle()

            if spotify_cache:
                task = ("insert", ("spotify", database_entries))
                self._append_task(lock_id, *task)
        except Exception as exc:
            lock(lock_id, False)
            raise exc
        finally:
            lock(lock_id, False)
        return track_list

    async def fetch_youtube_query(
        self,
        lock_id: int,
        track_info: str,
        current_cache_level: CacheLevel = CacheLevel.all(),
    ) -> Optional[str]:
        """Call the Youtube API and returns the youtube URL that the query matched."""
        track_url = await self._youtube_api.get_call(track_info)
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
            self._append_task(lock_id, *task)
        return track_url

    async def fetch_from_youtube_api(self, lock_id: int, track_info: str) -> Optional[str]:
        """Gets a YouTube URL from for the query."""
        cache_level = await self._config.cache_level()
        current_cache_level = CacheLevel(cache_level if cache_level else CacheLevel.all().value)
        cache_enabled = CacheLevel.set_youtube().is_subset(current_cache_level)
        val = None
        if cache_enabled:
            try:
                (val, update) = await self._local_cache_api.youtube.fetch_one(
                    {"track": track_info}
                )
            except Exception as exc:
                debug_exc_log(log, exc, "Failed to fetch %r from YouTube table", track_info)
        if val is None:
            try:
                youtube_url = await self.fetch_youtube_query(
                    lock_id, track_info, current_cache_level=current_cache_level
                )
            except YouTubeApiError as err:
                youtube_url = None
        else:
            if cache_enabled:
                task = ("update", ("youtube", {"track": track_info}))
                self._append_task(lock_id, *task)
            youtube_url = val
        return youtube_url

    async def fetch_track(
        self,
        lock_id: int,
        player: lavalink.Player,
        query: Query,
        forced: bool = False,
        lazy: bool = False,
        should_query_global: bool = False,
    ) -> Tuple[LoadResult, bool]:

        cache_level = await self._config.cache_level()
        current_cache_level = CacheLevel(cache_level if cache_level else CacheLevel.all().value)
        cache_enabled = CacheLevel.set_lavalink().is_subset(current_cache_level)
        val = None
        query = Query.process_input(query, self._path)
        query_string = str(query)
        globaldb_toggle = False
        valid_global_entry = False
        results = None
        called_api = False
        # prefer_lyrics = await self.cog.get_lyrics_status(ctx)
        # if prefer_lyrics and query.is_youtube and query.is_search:
        #     query_string = f"{query} - lyrics"
        if cache_enabled and not forced and not query.is_local:
            try:
                val, last_updated = await self._local_cache_api.lavalink.fetch_one(
                    {"query": query_string}
                )
            except Exception as exc:
                debug_exc_log(log, exc, "Failed to fetch %r from Lavalink table", query_string)

            if val and isinstance(val, dict):
                if IS_DEBUG:
                    log.debug("Updating Local Database with %r", query_string)
                task = ("update", ("lavalink", {"query": query_string}))
                self._append_task(lock_id, *task)
            else:
                val = None

            if val and not forced and isinstance(val, dict):
                valid_global_entry = False
                called_api = False
            else:
                val = None
        if (
            globaldb_toggle
            and not val
            and should_query_global
            and not forced
            and not query.is_local
            and not query.is_spotify
        ):
            valid_global_entry = False
            with contextlib.suppress(Exception):
                global_entry = await self._global_cache_api.get_call(query=query)
                if global_entry.get("loadType") == "V2_COMPACT":
                    global_entry["loadType"] = "V2_COMPAT"
                results = LoadResult(global_entry)
                if results.load_type in [
                    LoadType.PLAYLIST_LOADED,
                    LoadType.TRACK_LOADED,
                    LoadType.SEARCH_RESULT,
                    LoadType.V2_COMPAT,
                ]:
                    valid_global_entry = True
                if valid_global_entry:
                    if IS_DEBUG:
                        log.debug("Querying Global DB api for %r", query)
                    results, called_api = results, False
        if valid_global_entry:
            pass
        elif lazy is True:
            called_api = False
        elif val and not forced and isinstance(val, dict):
            data = val
            data["query"] = query_string
            if data.get("loadType") == "V2_COMPACT":
                data["loadType"] = "V2_COMPAT"
            results = LoadResult(data)
            called_api = False
            if results.has_error:
                # If cached value has an invalid entry make a new call so that it gets updated
                results, called_api = await self.fetch_track(lock_id, player, query, forced=True)
            valid_global_entry = False
        elif player:
            if IS_DEBUG:
                log.debug(f"Querying Lavalink api for {query_string}")
            called_api = True
            try:
                results = await player._ll_player.load_tracks(query_string)
            except KeyError:
                results = None
            except RuntimeError:
                raise TrackEnqueueError
        if results is None:
            results = LoadResult({"loadType": "LOAD_FAILED", "playlistInfo": {}, "tracks": []})
            valid_global_entry = False
        update_global = (
            globaldb_toggle and not valid_global_entry and self._global_cache_api.has_api_key
        )
        with contextlib.suppress(Exception):
            if (
                update_global
                and not query.is_local
                and not results.has_error
                and len(results.tracks) >= 1
            ):
                global_task = ("global", dict(llresponse=results, query=query))
                self._append_task(lock_id, *global_task)
        if (
            cache_enabled
            and results.load_type
            and not results.has_error
            and not query.is_local
            and results.tracks
        ):
            try:
                time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
                data = json.dumps(results._raw)
                if all(k in data for k in ["loadType", "playlistInfo", "isSeekable", "isStream"]):
                    task = (
                        "insert",
                        (
                            "lavalink",
                            [
                                {
                                    "query": query_string,
                                    "data": data,
                                    "last_updated": time_now,
                                    "last_fetched": time_now,
                                }
                            ],
                        ),
                    )
                    self._append_task(lock_id, *task)
            except Exception as exc:
                debug_exc_log(
                    log,
                    exc,
                    "Failed to enqueue write task for %r to Lavalink table",
                    query_string,
                )
        return results, called_api
