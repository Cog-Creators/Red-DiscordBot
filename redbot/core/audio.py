import logging
import discord
import lavalink
import pathlib
import time

from typing import Optional, Mapping, List, Union

from .audio_utils.errors import AudioError, LavalinkNotReady, NotConnectedToVoice, InvalidQuery, NoMatchesFound, TrackFetchError
from .audio_utils.audio_dataclasses import Query, _PARTIALLY_SUPPORTED_MUSIC_EXT

from redbot.core import Config
from redbot.core.utils import AsyncIter
from redbot.core.data_manager import cog_data_path
from redbot.core.audio_utils import Lavalink, AudioAPIInterface, ServerManager
from redbot.core.audio_utils.copied.audio_logging import IS_DEBUG

from redbot.core.audio_utils.copied.utils import CacheLevel, PlaylistScope

log = logging.getLogger("red.core.audio")
log_player = logging.getLogger("red.core.audio.Player")

_used_by = []
_players = {}
_api_interface = None
_lavalink = None
_server_manager = None
_config = None

async def initialize(
        bot,
        cog_name: str,
        identifier: int,
        force_restart_ll_server: bool = False,
        force_reset_db_conn: bool = False
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

        _config = Config.get_conf(None, identifier=2711759130, cog_name="Audio", force_registration=True)

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

async def shutdown(
        cog_name: str,
        identifier: int,
        force_shutdown: bool = False
):
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
            _api_interface.close()
        _used_by = []
    else:
        if not (cog_name, identifier) in _used_by:
            raise KeyError(f"{cog_name}: {identifier} doesn't match any established connection")

        if not _used_by:
            if _lavalink.is_connected:
                await _lavalink.shutdown()
            if _server_manager.is_running:
                await _server_manager.shutdown_ll_server()
            if _api_interface.is_connected:
                _api_interface.close()

async def connect(
        bot,
        channel: discord.VoiceChannel,
        deafen: bool = False
):
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

def get_player(guild: discord.Guild):
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
        return _players[guild.id]
    except KeyError:
        return None

def _get_ll_player(guild: discord.Guild) -> lavalink.Player:
    try:
        return lavalink.get_player(guild.id)
    except (KeyError, IndexError):
        raise NotConnectedToVoice("Bot is not currently connected to a voice channel")

def all_players():
    return list(_players.items())

class Player():
    def __init__(self, bot, channel):
        self._bot = bot
        self._player = lavalink.get_player(channel.guild.id)
        self._guild = channel.guild
        self._channel = channel
        self._config = _config
        self._local_folder_current_path = None
        self._lavalink = _lavalink
        self._api_interface = _api_interface
        self._server_manager = _server_manager

    @property
    def bot(self):
        return self._bot

    @property
    def channel(self):
        """discord.VoiceChannel: The current voice channel"""
        return self._channel

    @property
    def current(self):
        """lavalink.Track: The current track"""
        return self.player.current

    @property
    def guild(self):
        """discord.Guild: The player's guild"""
        return self._guild

    @property
    def paused(self):
        """bool: Whether or not the player is paused"""
        return self.player.paused

    @property
    def player(self):
        """lavalink.Player: The lavalink.Player behind this object"""
        return self._player

    @property
    def position(self):
        """float: Position of the current song"""
        return self.player.position

    @property
    async def queue(self):
        """list: The player's queue"""
        return self.player.queue

    @queue.setter
    def queue(self, q: List):
        self.player.queue = q

    @property
    def repeat(self):
        """bool: Whether or not the queue repeats"""
        return self.player.repeat

    @repeat.setter
    def repeat(self, r: bool):
        self.player.repeat = r

    @property
    def shuffle(self):
        """bool: Whether or not the queue is shuffled"""
        return self.player.shuffle

    @shuffle.setter
    def shuffle(self, s: bool):
        self.player.shuffle = s

    @property
    def shuffle_bumped(self):
        return self.player.shuffle_bumped

    @shuffle_bumped.setter
    def shuffle_bumped(self, sb: bool):
        self.player.shuffle_bumped = sb

    @property
    async def volume(self):
        """The player's volume
        :type: int"""
        return self.player.volume

    @property
    def is_playing(self):
        """Whether or not the player is playing
        :type: bool"""
        return self.player.is_playing

    async def _set_player_settings(self, player: lavalink.Player) -> None:
        guild_data = await self._config.guild(self._guild).all()
        player.repeat = guild_data["repeat"]
        player.shuffle = guild_data["shuffle"]
        player.shuffle_bumped = guild_data["shuffle_bumped"]
        volume = guild_data["volume"]
        if player.volume != volume:
            await player.set_volume(volume)

    async def _enqueue_tracks(self, query: str, player: lavalink.Player, requester: discord.Member, enqueue: bool = True):
        settings = await self._config.guild(self._guild).all()
        settings["maxlength"] = 0 if not "maxlength" in settings.keys() else settings["maxlength"]

        local_folder = None

        first_track_only = False
        index = None
        seek = 0

        query = Query.process_input(query, local_folder)
        #tracks, playlist_data = await self.get_tracks(query._raw, requester.guild, local_folder)

        if not isinstance(query, list):
            if query.single_track:
                first_track_only = True
                index = query.track_index
                if query.start_time:
                    seek = query.start_time

            try:
                result, called_api = await self._api_interface.fetch_track(
                    requester.id, player, query
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
                    log_player.debug("Semi supported file extension: Track might not be fully playable")
                raise TrackFetchError("Fetching tracks failed")

        else:
            tracks = query

        if not tracks:
            return

        if not first_track_only and len(tracks) > 1:
            if len(player.queue) >= 10000:
                log_player.debug("Queue limit reached")
            track_len = 0
            empty_queue = not player.queue
            async for track in AsyncIter(tracks):
                if len(player.queue) >= 10000:
                    log_player.debug("Queue limit reached")
                    break

                if settings["maxlength"] > 0:
                    track_len += 1
                    track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": player.channel.id,
                            "requester": requester.id
                        }
                    )
                    player.add(requester, track)
                    self._bot.dispatch(
                        "red_audio_track_enqueue", self._guild, track, requester
                    )
                else:
                    track_len += 1
                    track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": player.channel.id,
                            "requester": requester.id
                        }
                    )
                    player.add(requester, track)
                    self._bot.dispatch(
                        "red_audio_track_enqueue", self._guild, track, requester
                    )
            player.maybe_shuffle(0 if empty_queue else 1)

            if len(tracks) > track_len:
                log_player.debug(f"{len(tracks) - track_len} tracks cannot be enqueued")

            if not player.current:
                await player.play()
            return tracks, playlist_data

        else:
            try:
                if len(player.queue) >= 10000:
                    log_player.debug("Queue limit reached")

                single_track = (
                    tracks if isinstance(tracks, lavalink.rest_api.Track)
                    else tracks[index] if index else tracks[0]
                )

                if seek and seek > 0:
                    single_track.start_timestamp = seek * 1000

                if settings["maxlength"] > 0:
                    player.add(requester, single_track)
                    self._bot.dispatch(
                        "red_audio_track_enqueue", self._guild, single_track, requester
                    )
                    player.maybe_shuffle()

                else:
                    single_track.extras.update(
                        {
                            "enqueue_time": int(time.time()),
                            "vc": player.channel.id,
                            "requester": requester.id
                        }
                    )
                    player.add(requester, single_track)
                    self._bot.dispatch(
                        "red_audio_track_enqueue", self._guild, single_track, requester
                    )
                    player.maybe_shuffle()
            except IndexError:
                raise InvalidQuery(f"No results found for {query}")
            except Exception as e:
                raise e

        if not player.current:
            log_player.debug("Starting player")
            await player.play()
        return single_track, None

    async def _skip(self, player: lavalink.Player, requester: Union[discord.User, discord.Member], skip_to_track: int = None) -> None:
        autoplay = await self._config.guild(self._guild).auto_play()
        if not player.current or (not player.queue and not autoplay):
            raise AudioError("Nothing in the queue")

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

        player = self.player

        try:
            result, called_api = await self._api_interface.fetch_track(
                self._guild.id, player, query
            )
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
                log_player.debug("Semi supported file extension: Track might not be fully playable")
        return tracks, playlist_data

    async def play(self, query: str, requester: discord.Member, local_folder: pathlib.Path = None):
        """Plays a track

        Parameters
        ----------
        query: str
            The query to search for. Supports everything core audio supports
        requester: discord.Member
            The requester of the song
        local_folder: pathlib.Path
            Local folder if track is a local track
        Returns
        -------
        List[lavalink.Track], playlist_data
        """
        player = self.player

        await self._set_player_settings(player)

        tracks, playlist_data = await self._enqueue_tracks(query, player, requester)

        return tracks, playlist_data

    async def pause(self) -> None:
        """Pauses the player in a guild"""
        player = self.player

        if not player.paused:
            await player.pause()
            self._bot.dispatch(
                "red_audio_audio_paused", self._guild, True
            )

    async def resume(self) -> None:
        """Resumes the player in a guild"""
        player = self.player

        if player.paused:
            await player.pause(False)
            self._bot.dispatch(
                "red_audio_audio_paused", self._guild, False
            )

    async def skip(self, requester: discord.Member,
                   skip_to_track: int = None) -> lavalink.Track:
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
        player = self.player

        await self._skip(player, requester, skip_to_track)

    async def stop(self) -> None:
        """Stop the playback"""
        player = self.player
        player.queue = []
        player.store("playing_song", None)
        player.store("prev_requester", None)
        player.store("prev_song", None)
        player.store("requester", None)
        player.store("autoplay_notified", False)
        await player.stop()

        self._bot.dispatch("red_audio_audio_stop", self._guild)

    async def move_to(self, channel: discord.VoiceChannel) -> None:
        """Move the player to another voice channel

        Parameters
        ----------
        channel: discord.VoiceChannel
            The channel to move the player to
        """
        player = self.player
        self.channel = channel

        await player.move_to(channel)

    async def disconnect(self) -> None:
        """Disconnects the player"""
        global _players

        player = self.player
        channel = player.channel

        player.queue = []
        player.store("playing_song", None)
        player.store("autoplay_notified", False)
        await player.stop()
        self._bot.dispatch("red_audio_audio_stop", self._guild)
        await player.disconnect()
        self._bot.dispatch("red_audio_audio_disconnect", self._guild)

        if IS_DEBUG:
            log_player.debug(f"Disconnected from {channel} in {self._guild}")

        del _players[self._guild.id]
        del self

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
        self.player.volume = vol

