from __future__ import annotations

import logging
import discord
import lavalink
import pathlib
import time
import re
import asyncio

from typing import Optional, Mapping, List

from .audio_utils.errors import (
    AudioError,
    LavalinkNotReady,
    NotConnectedToVoice,
    InvalidQuery,
    NoMatchesFound,
    TrackFetchError,
    SpotifyFetchError,
)
from .audio_utils.audio_dataclasses import Query, _PARTIALLY_SUPPORTED_MUSIC_EXT

from redbot.core import Config
from redbot.core.utils import AsyncIter
from redbot.core.data_manager import cog_data_path
from redbot.core.audio_utils import Lavalink, AudioAPIInterface, ServerManager
from redbot.core.audio_utils.audio_logging import IS_DEBUG

from redbot.core.audio_utils.utils import CacheLevel, PlaylistScope

log = logging.getLogger("red.core.audio")
log_player = logging.getLogger("red.core.audio.Player")

_used_by: list = []
_players: dict = {}
_api_interface: Optional[AudioAPIInterface] = None
_lavalink: Optional[Lavalink] = None
_server_manager: Optional[ServerManager] = None
_config: Optional[Config] = None


async def initialize(
    bot,
    cog_name: str,
    identifier: int,
    force_restart_ll_server: bool = False,
    force_reset_db_conn: bool = False,
):
    """Initializes the api and establishes all connections

    Parameters
    ----------
    bot: Red
        The bot object
    cog_name: str
        Cog name used to track api usage
    identifier: int
        Unique identifier to counteract similar cog_names
    force_restart_ll_server: bool
        Force restarts the lavalink sever if set to True
    force_reset_db_conn: bool
        Force resets the database connection"""
    global _used_by

    if not _used_by:
        global _config, _lavalink, _server_manager, _api_interface

        _config = Config.get_conf(
            None, identifier=2711759130, cog_name="Audio", force_registration=True
        )

        _default_lavalink_settings = {
            "host": "localhost",
            "rest_port": 2333,
            "ws_port": 2333,
            "password": "youshallnotpass",
        }

        default_global = {
            "schema_version": 1,
            "bundled_playlist_version": 0,
            "owner_notification": 0,
            "cache_level": CacheLevel.all().value,
            "cache_age": 365,
            "daily_playlists": False,
            "global_db_enabled": False,
            "global_db_get_timeout": 5,
            "status": False,
            "use_external_lavalink": False,
            "restrict": True,
            "localpath": str(cog_data_path(raw_name="Audio")),
            "url_keyword_blacklist": [],
            "url_keyword_whitelist": [],
            "java_exc_path": "java",
            **_default_lavalink_settings,
        }

        default_guild = {
            "auto_play": False,
            "currently_auto_playing_in": None,
            "auto_deafen": True,
            "autoplaylist": {
                "enabled": True,
                "id": 42069,
                "name": "Aikaterna's curated tracks",
                "scope": PlaylistScope.GLOBAL.value,
            },
            "persist_queue": True,
            "disconnect": False,
            "dj_enabled": False,
            "dj_role": None,
            "daily_playlists": False,
            "emptydc_enabled": False,
            "emptydc_timer": 0,
            "emptypause_enabled": False,
            "emptypause_timer": 0,
            "jukebox": False,
            "jukebox_price": 0,
            "maxlength": 0,
            "max_volume": 150,
            "notify": False,
            "prefer_lyrics": False,
            "repeat": False,
            "shuffle": False,
            "shuffle_bumped": True,
            "thumbnail": False,
            "volume": 100,
            "vote_enabled": False,
            "vote_percent": 0,
            "room_lock": None,
            "url_keyword_blacklist": [],
            "url_keyword_whitelist": [],
            "country_code": "US",
        }
        _playlist: Mapping = dict(id=None, author=None, name=None, playlist_url=None, tracks=[])

        _config.init_custom("EQUALIZER", 1)
        _config.register_custom("EQUALIZER", eq_bands=[], eq_presets={})
        _config.init_custom(PlaylistScope.GLOBAL.value, 1)
        _config.register_custom(PlaylistScope.GLOBAL.value, **_playlist)
        _config.init_custom(PlaylistScope.GUILD.value, 2)
        _config.register_custom(PlaylistScope.GUILD.value, **_playlist)
        _config.init_custom(PlaylistScope.USER.value, 2)
        _config.register_custom(PlaylistScope.USER.value, **_playlist)
        _config.register_guild(**default_guild)
        _config.register_global(**default_global)
        _config.register_user(country_code=None)

        _api_interface = AudioAPIInterface(bot, _config)
        _server_manager = ServerManager(bot, _config)
        _lavalink = Lavalink(bot, _config, _server_manager, _api_interface)

    if force_restart_ll_server:
        if _server_manager.is_running:
            await _lavalink.shutdown()
            await _server_manager.shutdown_ll_server()

    if force_reset_db_conn:
        if _api_interface.is_connected:
            await _api_interface.close()

    if not _lavalink.is_connected:
        await _lavalink.start()

    if not _api_interface.is_connected:
        await _api_interface.initialize()

    _used_by.append((cog_name, identifier))


async def shutdown(cog_name: str, identifier: int, force_shutdown: bool = False):
    """Closes the api connection

    Parameters
    ----------
    cog_name: str
        The same cog name used in :py:meth:initialize
    identifier: int
        The same identifier used in :py:meth:initialize
    force_shutdown: bool
        whether or not the connection should be force closed,
        even though other cogs are still connected"""
    global _used_by

    if force_shutdown:
        if _lavalink.is_connected:
            await _lavalink.shutdown()
        if _server_manager.is_running:
            await _server_manager.shutdown_ll_server()
        if _api_interface.is_connected:
            await _api_interface.run_all_pending_tasks()
            await _api_interface.close()
        _used_by = []
    else:
        if not (cog_name, identifier) in _used_by:
            raise KeyError(f"{cog_name}: {identifier} doesn't match any established connection")

        _used_by.remove((cog_name, identifier))

        if not _used_by:
            if _lavalink.is_connected:
                await _lavalink.shutdown()
            if _server_manager.is_running:
                await _server_manager.shutdown_ll_server()
            if _api_interface.is_connected:
                await _api_interface.run_all_pending_tasks()
                await _api_interface.close()


async def wait_until_api_ready():
    while True:
        if _used_by:
            break
        await asyncio.sleep(0.1)


async def connect(bot, channel: discord.VoiceChannel, deafen: bool = False):
    """Connects to a voice channel

    Parameters
    ----------
    bot: Red
        The bot object
    channel: discord.VoiceChannel
        The channel to connect to
    deafen: bool
        Overwrites the configs auto_deafen value if given
    Returns
    -------
    Player: Player
        A player object"""
    if not _lavalink and not _lavalink.is_connected:
        raise LavalinkNotReady("Connection to lavalink has not yet been established")

    if not deafen:
        deafen = await _config.guild(channel.guild).auto_deafen()
    await lavalink.connect(channel=channel, deafen=deafen)

    player = Player(bot, channel)
    _players[channel.guild.id] = player
    return player


def get_player(guild_id: int) -> Optional[Player]:
    """Get the Player object of the given guild

    Parameters
    ----------
    guild: discord.Guild
        The guild to get the Player object from
    Returns
    -------
    Player: Optional[Player]
        The Player object of this guild"""
    try:
        return _players[guild_id]
    except KeyError:
        return None


async def dj_enabled(guild: discord.Guild):
    """Whether or not DJ controls are enabled

    Parameters
    ----------
    guild: discord.Guild
        The guild for which to check
    Returns
    -------
    bool
        Whether or not DJ controls are enabled"""

    if await _config.guild(guild).dj_enabled():
        return True

    return False


async def is_dj(user: discord.Member):
    """Whether ot not a user has the DJ role

    Parameters
    ----------
    user: discord.Member
        The user to check for
    Returns
    -------
    bool
        Whether or not the user has the DJ role"""

    dj_role = await _config.guild(user.guild).dj_role()

    if not dj_role:
        return False

    dj_role = user.guild.get_role(dj_role)
    if dj_role in user.roles:
        return True

    return False


def _get_ll_player(guild: discord.Guild) -> lavalink.Player:
    try:
        return lavalink.get_player(guild.id)
    except (KeyError, IndexError):
        raise NotConnectedToVoice("Bot is not currently connected to a voice channel")


def all_players():
    return list(_players.values())


class Player:
    def __init__(self, bot, channel):
        self._bot = bot
        self._player = lavalink.get_player(channel.guild.id)
        self._guild = channel.guild
        self._config = _config
        self._local_folder_current_path = None
        self._lavalink = _lavalink
        self._api_interface = _api_interface
        self._server_manager = _server_manager

    def __repr__(self):
        return (
            "<Player: "
            f"guild={self.guild.name!r} ({self.guild.id}), "
            f"channel={self.channel.name!r} ({self.channel.id}), "
            f"playing={self.is_playing}, paused={self.paused}, volume={self.volume}, "
            f"queue_size={len(self.queue)}, current={self.current!r}, "
            f"position={self.position}, "
            f"length={self.current.length if self.current else 0}>"
        )

    @property
    def bot(self):
        return self._bot

    @property
    def channel(self):
        """discord.VoiceChannel: The current voice channel"""
        return self._player.channel

    @property
    def current(self):
        """lavalink.Track: The current track"""
        return self._player.current

    @property
    def guild(self):
        """discord.Guild: The player's guild"""
        return self._guild

    @property
    def is_playing(self):
        """Whether or not the player is playing
        :type: bool"""
        return self._player.is_playing

    @property
    def paused(self):
        """bool: Whether or not the player is paused"""
        return self._player.paused

    @property
    def _ll_player(self):
        """lavalink.Player: The lavalink.Player behind this object"""
        return self._player

    @property
    def position(self):
        """float: Position of the current song"""
        return self._player.position

    @property
    def queue(self):
        """list: The player's queue"""
        return self._player.queue

    @queue.setter
    def queue(self, q: List):
        self._player.queue = q

    @property
    def repeat(self):
        """bool: Whether or not the queue repeats"""
        return self._player.repeat

    @repeat.setter
    def repeat(self, r: bool):
        self._player.repeat = r

    @property
    def shuffle(self):
        """bool: Whether or not the queue is shuffled"""
        return self._player.shuffle

    @shuffle.setter
    def shuffle(self, s: bool):
        self._player.shuffle = s

    @property
    def shuffle_bumped(self):
        return self._player.shuffle_bumped

    @shuffle_bumped.setter
    def shuffle_bumped(self, sb: bool):
        self._player.shuffle_bumped = sb

    @property
    def volume(self):
        """The player's volume
        :type: int"""
        return self._player.volume

    async def _set_player_settings(self) -> None:
        guild_data = await self._config.guild(self._guild).all()
        self.repeat = guild_data["repeat"]
        self.shuffle = guild_data["shuffle"]
        self.shuffle_bumped = guild_data["shuffle_bumped"]
        volume = guild_data["volume"]
        if self.volume != volume:
            await self.set_volume(volume)

    async def _add_to_queue(
        self,
        requester: discord.Member,
        track: lavalink.Track,
        bump: bool = False,
        bump_and_skip: bool = False,
    ):

        track.requester = requester
        if not bump and not bump_and_skip:
            self.queue.append(track)
        elif bump or bump_and_skip:
            self.queue.insert(0, track)
            if bump_and_skip:
                if self.current:
                    await self.skip(requester)

    async def _enqueue_tracks(
        self,
        requester: discord.Member,
        query: Optional[str],
        track: Optional[lavalink.Track],
        local_folder: Optional[pathlib.Path],
        bump: bool = False,
        bump_and_skip: bool = False,
        enqueue: bool = True,
    ):
        settings = await self._config.guild(self._guild).all()
        settings["maxlength"] = 0 if not "maxlength" in settings.keys() else settings["maxlength"]

        first_track_only = False
        index = None
        seek = 0

        if track:
            if len(self.queue) >= 10000:
                log_player.debug("Queue limit reached")

            if seek and seek > 0:
                track.start_timestamp = seek * 1000

            if settings["maxlength"] > 0:
                await self._add_to_queue(requester, track, bump, bump_and_skip)
                self._bot.dispatch("red_audio_track_enqueue", self._guild, track, requester)
                self.maybe_shuffle()

            else:
                track.extras.update(
                    {
                        "enqueue_time": int(time.time()),
                        "vc": self.channel.id,
                        "requester": requester.id,
                    }
                )
                await self._add_to_queue(requester, track, bump, bump_and_skip)
                self._bot.dispatch("red_audio_track_enqueue", self._guild, track, requester)
                self.maybe_shuffle()
                if not self.current:
                    await self._player.play()
                return track, None

        query = Query.process_input(query, local_folder)
        if query.is_spotify:
            return await self._enqueue_spotify_tracks(requester, query, bump, bump_and_skip)

        if not isinstance(query, list):
            if query.single_track:
                first_track_only = True
                index = query.track_index
                if query.start_time:
                    seek = query.start_time

            try:
                result, called_api = await self._api_interface.fetch_track(
                    requester.id, self._player, query
                )
            except KeyError:
                raise NoMatchesFound("No matches could be found for the given query")

            tracks = result.tracks
            playlist_data = result.playlist_info
            if not enqueue:
                return tracks
            if not tracks:
                if IS_DEBUG:
                    if result.exception_message:
                        if "Status Code" in result.exception_message:
                            log_player.debug(result.exception_message[:2000])
                        else:
                            log_player.debug(result.exception_message[:2000].replace("\n", ""))
                if await self._config.use_external_lavalink() and query.is_local:
                    log_player.debug("Local track")
                elif query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                    log_player.debug(
                        "Semi supported file extension: Track might not be fully playable"
                    )
                raise TrackFetchError("Fetching tracks failed")

        else:
            tracks = query

        if not tracks:
            return

        if not first_track_only and len(tracks) > 1:
            if len(self.queue) >= 10000:
                log_player.debug("Queue limit reached")
            track_len = 0
            empty_queue = not self.queue
            async for track in AsyncIter(tracks):
                if len(self.queue) >= 10000:
                    log_player.debug("Queue limit reached")
                    break

                if settings["maxlength"] > 0:
                    track_len += 1
                    track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": self.channel.id,
                            "requester": requester.id,
                        }
                    )
                    await self._add_to_queue(requester, track, bump, bump_and_skip)
                    self._bot.dispatch("red_audio_track_enqueue", self._guild, track, requester)
                else:
                    track_len += 1
                    track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": self.channel.id,
                            "requester": requester.id,
                        }
                    )
                    await self._add_to_queue(requester, track, bump, bump_and_skip)
                    self._bot.dispatch("red_audio_track_enqueue", self._guild, track, requester)
            self.maybe_shuffle(0 if empty_queue else 1)

            if len(tracks) > track_len:
                log_player.debug(f"{len(tracks) - track_len} tracks cannot be enqueued")

            if not self.current:
                await self._player.play()
            return tracks, playlist_data

        else:
            try:
                if len(self.queue) >= 10000:
                    log_player.debug("Queue limit reached")

                single_track = (
                    tracks
                    if isinstance(tracks, lavalink.rest_api.Track)
                    else tracks[index]
                    if index
                    else tracks[0]
                )

                if seek and seek > 0:
                    single_track.start_timestamp = seek * 1000

                if settings["maxlength"] > 0:
                    await self._add_to_queue(requester, single_track, bump, bump_and_skip)
                    self._bot.dispatch(
                        "red_audio_track_enqueue", self._guild, single_track, requester
                    )
                    self.maybe_shuffle()

                else:
                    single_track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": self.channel.id,
                            "requester": requester.id,
                        }
                    )
                    await self._add_to_queue(requester, single_track, bump, bump_and_skip)
                    self._bot.dispatch(
                        "red_audio_track_enqueue", self._guild, single_track, requester
                    )
                    self.maybe_shuffle()
            except IndexError:
                raise InvalidQuery(f"No results found for {query}")
            except Exception as e:
                raise e

        if not self.current:
            log_player.debug("Starting player")
            await self._player.play()
        return single_track, None

    async def _enqueue_spotify_tracks(
        self,
        requester: discord.Member,
        query: Query,
        bump: bool = False,
        bump_and_skip: bool = False,
    ):
        if query.single_track:
            try:
                res = await self._api_interface.spotify_query(
                    requester.id, "track", query.id, skip_youtube=True
                )
                if not res:
                    raise NoMatchesFound("No tracks which match your query found on spotify")
            except Exception as e:
                raise e

            new_query = Query.process_input(res[0], None)
            new_query.start_time = query.start_time
            return await self._enqueue_tracks(
                requester,
                query=new_query,
                track=None,
                local_folder=None,
                bump=bump,
                bump_and_skip=bump_and_skip,
            )

        elif query.is_album or query.is_playlist:
            # ToDo fetch spotify playlists: utilities/player.py L#336
            pass

    async def _skip(
        self, player: lavalink.Player, requester: discord.Member, skip_to_track: int = None
    ) -> None:
        autoplay = await self._config.guild(self._guild).auto_play()
        if not player.current:
            raise AudioError("Nothing playing")

        elif autoplay and not player.queue:
            await player.skip()
            return

        queue_to_append = []
        if skip_to_track and skip_to_track != 1:
            if skip_to_track > len(player.queue):
                raise IndexError("skip_to_track cannot be larger than the total queue length")

            if player.repeat:
                queue_to_append = player.queue[0 : min(skip_to_track - 1, len(player.queue) - 1)]
            player.queue = player.queue[
                min(skip_to_track - 1, len(player.queue) - 1) : len(player.queue)
            ]
        self._bot.dispatch("red_audio_track_skip", self._guild, player.current, requester)
        await player.play()
        player.queue += queue_to_append

    async def disconnect(self) -> None:
        """Disconnects the player"""
        global _players

        await self.stop()
        await self._player.disconnect()
        self._bot.dispatch("red_audio_audio_disconnect", self._guild)

        if IS_DEBUG:
            log_player.debug(f"Disconnected from {self.channel} in {self._guild}")

        del _players[self._guild.id]
        del self

    async def get_tracks(self, query: str, local_folder: pathlib.Path = None):
        """Queries the local apis for a track and falls back to lavalink if none was found
        Note: falling back to lavalink is only possible if the bot is connected to a voice channel

        Parameters
        ----------
        query: str
            The query to search for. Supports everything core audio supports
        local_folder: pathlib.Path
            Local folder if track is a local track
        Returns
        -------
        List[lavalink.Track], playlist_data
        """
        query = Query.process_input(query, local_folder)
        if not query.valid:
            raise InvalidQuery(f"No results found for {query}")

        try:
            result, called_api = await self._api_interface.fetch_track(self._guild.id, self, query)
        except KeyError:
            raise NoMatchesFound("No matches could be found for the given query")

        tracks = result.tracks
        playlist_data = result.playlist_info

        if not tracks:
            if result.exception_message:
                if IS_DEBUG:
                    if "Status Code" in result.exception_message:
                        log_player.debug(result.exception_message[:2000])
                    else:
                        log_player.debug(result.exception_message[:2000].replace("\n", ""))
                raise TrackFetchError("Fetching tracks failed")
            if await self._config.use_external_lavalink() and query.is_local:
                log_player.debug("Local track")
            elif query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                log_player.debug(
                    "Semi supported file extension: Track might not be fully playable"
                )
        return tracks, playlist_data

    async def get_local_tracks(self, query: pathlib.Path):
        """Converts a localtrack into a lavalink.Track object which can then be used in Player.play

        Parameters
        ----------
        query: pathlib.Path
            path to the music file
        Returns
        -------
        List[lavalink.Track], playlist_data
        """
        load_result = await self._player.load_tracks(str(query))
        if load_result.tracks:
            return load_result.tracks, load_result.playlist_info
        else:
            if load_result.exception_message:
                log.exception(load_result.exception_message)
            else:
                raise AudioError("Track lookup failed.")

    def fetch(self, key, default=None):
        """Returns a stored metadata value.

        Parameters
        ----------
        key
            Key used to store metadata.
        default
            Optional, used if the key doesn't exist.
        """
        return self._player._metadata.get(key, default)

    async def is_requester(self, member: discord.Member) -> bool:
        """Whether a user is the requester of the current song

        Parameters
        ----------
        member: discord.Member
            Member to check
        Returns
        -------
        bool
        """
        if self.current:
            if self.current.requester.id == member.id:
                return True
        return False

    def maybe_shuffle(self, sticky_songs: int = 1):
        """Shuffles the queue if shuffle is True"""
        if self.shuffle and self.queue:
            self._player.force_shuffle(sticky_songs)

    async def move_to(self, channel: discord.VoiceChannel, deafen: bool = True) -> None:
        """Move the player to another voice channel

        Parameters
        ----------
        channel: discord.VoiceChannel
            The channel to move the player to
        deafen: bool
            Whether or not the player deafens
        """
        if channel != self.channel:
            player = self._player

            await player.move_to(channel)

            # player._last_channel_id = self.channel.id
            # player.channel = channel
            #
            # await player.connect(True)

    async def pause(self) -> None:
        """Pauses the player in a guild"""
        player = self._player

        if not player.paused:
            await player.pause()
            self._bot.dispatch("red_audio_audio_paused", self._guild, True)

    async def play(
        self,
        requester: discord.Member,
        query: Optional[str] = None,
        track: Optional[lavalink.Track] = None,
        local_folder: pathlib.Path = None,
        bump: bool = False,
        bump_and_skip: bool = False,
    ):
        """Plays a track

        Parameters
        ----------
        requester: discord.Member
            The requester of the song
        query: str
            The query to search for. Supports everything core audio supports
        track: lavalink.Track
            A track object to be enqueued
        local_folder: pathlib.Path
            Local folder if track is a local track
        bump: bool
            Puts the song at queue position 0 if True
        bump_and_skip: bool
            acts like bump but also skips the current song
        Returns
        -------
        List[lavalink.Track], playlist_data
        """
        if not query and not track:
            raise AttributeError("Either a query string or a track object is required")

        await self._set_player_settings()

        tracks, playlist_data = await self._enqueue_tracks(
            requester,
            query=query,
            track=track,
            local_folder=local_folder,
            bump=bump,
            bump_and_skip=bump_and_skip,
        )

        await self._api_interface.run_tasks(requester.id)
        return tracks, playlist_data

    async def resume(self) -> None:
        """Resumes the player in a guild"""

        if self.paused:
            await self._player.pause(False)
            self._bot.dispatch("red_audio_audio_paused", self._guild, False)

    async def seek(self, seconds: int = None, timestamp: str = None):
        """Skip to a given position or skips a given amount of seconds

        Parameters
        ----------
        seconds: int
            Seconds to skip. Can be a negative number to go backwards
        timestamp: str
            timestamp to skip to
            Expected format: hh:mm:ss -> 00:10:15 for example"""
        if self.current:
            if self.current.is_stream:
                raise AudioError("Cannot seek streams")

            if not self.current.seekable:
                raise AudioError("Track is not seekable")

            if seconds:
                if seconds * 1000 > self.current.length - self.position:
                    raise ValueError(
                        "Cannot seek for more time than the current track has remaining"
                    )

                seek = self.position + seconds * 1000
                await self._player.seek(seek)
                return

            elif timestamp:
                match = (re.compile(r"(?:(\d+):)?([0-5]?[0-9]):([0-5][0-9])")).match(seconds)
                if match is not None:
                    hr = int(match.group(1)) if match.group(1) else 0
                    mn = int(match.group(2)) if match.group(2) else 0
                    sec = int(match.group(3)) if match.group(3) else 0
                    seek = sec + (mn * 60) + (hr * 3600)
                else:
                    try:
                        seek = int(seconds)
                    except ValueError:
                        seek = 0

                await self._player.seek(seek)

            else:
                raise AttributeError("Either seconds or timestamp has to be given")

    async def set_volume(self, vol: int) -> int:
        """Set the player's volume

        Returns
        -------
        int
            the volume after change
        """

        max_vol = await self._config.guild(self.guild).max_volume()
        if vol < 0 or vol > max_vol:
            raise ValueError("Volume is not within the allowed range")

        await self._config.guild(self._guild).volume.set(vol)
        await self._player.set_volume(vol)

    async def skip(self, requester: discord.Member, skip_to_track: int = None) -> lavalink.Track:
        """Skips a track

        Parameters
        ----------
        requester: discord.Member
            The requester of the skip
        skip_to_track: int
            Amount of tracks you want to skip
        Returns
        -------
        lavalink.Track
            The current track
        """
        player = self._player

        await self._skip(player, requester, skip_to_track)

    async def stop(self) -> None:
        """Stop the playback"""
        self.queue = []
        self.store("playing_song", None)
        self.store("prev_requester", None)
        self.store("prev_song", None)
        self.store("requester", None)
        self.store("autoplay_notified", False)
        await self._player.stop()

        self._bot.dispatch("red_audio_audio_stop", self._guild)

    def store(self, key, value) -> None:
        """Stores a metadata value by key."""
        self._player._metadata[key] = value
