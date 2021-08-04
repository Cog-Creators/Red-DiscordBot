import logging
import discord
import lavalink
import pathlib
import time
import contextlib

from typing import Optional, Mapping, ClassVar, List, Union

from .audio_utils import Lavalink, AudioAPIInterface, ServerManager

from .audio_utils.errors import AudioError, LavalinkNotReady, NotConnectedToVoice, InvalidQuery, NoMatchesFound, TrackFetchError
from .audio_utils.audio_dataclasses import Query, _PARTIALLY_SUPPORTED_MUSIC_EXT
from .audio_utils.api_utils import _ValueCtxManager

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter
from redbot.core.data_manager import cog_data_path
from redbot.core.audio_utils.copied.audio_logging import IS_DEBUG

from redbot.core.audio_utils.copied.utils import CacheLevel, PlaylistScope

log = logging.getLogger("red.core.audio")
log_player = logging.getLogger("red.core.audio.Player")


class Audio:
    _used_by: ClassVar[List] = []

    def __init__(self, bot):
        self._used_by = []
        self._bot = bot
        self._local_folder_current_path = None
        self._session = None

        self._config = Config.get_conf(None, identifier=2711759130, cog_name="Audio", force_registration=True)

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

        self._config.init_custom("EQUALIZER", 1)
        self._config.register_custom("EQUALIZER", eq_bands=[], eq_presets={})
        self._config.init_custom(PlaylistScope.GLOBAL.value, 1)
        self._config.register_custom(PlaylistScope.GLOBAL.value, **_playlist)
        self._config.init_custom(PlaylistScope.GUILD.value, 2)
        self._config.register_custom(PlaylistScope.GUILD.value, **_playlist)
        self._config.init_custom(PlaylistScope.USER.value, 2)
        self._config.register_custom(PlaylistScope.USER.value, **_playlist)
        self._config.register_guild(**default_guild)
        self._config.register_global(**default_global)
        self._config.register_user(country_code=None)

        self.api_interface = AudioAPIInterface(self._bot, self._config)
        self.server_manager = ServerManager(self._bot, self._config)
        self.lavalink = Lavalink(self._bot, self._config, self.server_manager, self.api_interface)
        self._player = Player(self._bot, self._config, self.lavalink, self.api_interface)

    @property
    def player(self):
        return self._player

    @property
    def config(self):
        return self._config

    @classmethod
    async def initialize(
            cls,
            bot,
            cog_name: str,
            identifier: int,
            force_restart_ll_server: bool = False,
            force_reset_db_connection: bool = False,
    ):
        """Initializes the api and establishes the connection to lavalink

        Parameters
        ----------
        bot: Red
            The bot object to establish the connection to
        cog_name: str
            Used to detect whether the api is used by which cogs
        identifier: int
            Used to prevent shutdown if cog_name is the same between connections
        force_restart_ll_server: bool
            Whether the lavalink server should be restarted if it is currently running
        force_reset_db_connection: bool
            Whether the database connection should be reset if it is currently connected

        Returns
        -------
        cls: Audio
            An instance of the api
        """
        if not cls._used_by:
            audio_class = cls(bot)
            bot.audio_class = audio_class
        else:
            audio_class = bot.audio_class

        if force_restart_ll_server:
            if audio_class.server_manager.is_running:
                await audio_class.server_manager.shutdown_ll_server()

        if force_reset_db_connection:
            if audio_class.api_interface.is_connected:
                audio_class.api_interface.close()

        if not audio_class.api_interface.is_connected:
            await audio_class.api_interface.initialize()

        if not audio_class.lavalink.is_connected:
            await audio_class.lavalink.start()

        cls._used_by.append((cog_name, identifier))

        return audio_class

    @classmethod
    async def stop(
            cls,
            bot,
            cog_name: str,
            identifier: int,
            force_shutdown: bool = False
    ) -> None:
        """Closes the lavalink connection and shuts the server down if unused

        Parameters
        ----------
        bot: Red
            The bot object to close the connection from
        cog_name: str
            Used to detect whether the api is used by which cogs
        identifier: int
            Used to prevent shutdown if cog_name is the same between connections
        force_shutdown: bool
            Shutdown all servers, even though other cogs still use it
        """

        if not force_shutdown:
            if not (cog_name, identifier) in cls._used_by:
                raise KeyError(f"{cog_name}: {identifier} doesn't match any established connection")

        audio_class = bot.audio_class
        if not audio_class:
            return

        cls._used_by.remove((cog_name, identifier))

        if not cls._used_by:
            if audio_class.server_manager.is_running:
                await audio_class.server_manager.shutdown_ll_server()

            if audio_class.api_interface.is_connected:
                audio_class.api_interface.close()

            if audio_class.lavalink.is_connected:
                await audio_class.lavalink.shutdown()

    @classmethod
    def get_player(cls, guild: discord.Guild) -> Optional[lavalink.Player]:
        """Returns the lavalink player object for a guild

        Parameters
        ----------
        guild: discord.Guild
            The guild for which the player should be returned
        Returns
        -------
        Optional[lavalink.Player]
            The Player object of the given guild"""

        try:
            return lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            return None

class Player:
    def __init__(self, bot, config, lavalink, api_interface):
        self._bot = bot
        self._config = config
        self._local_folder_current_path = None
        self._lavalink = lavalink
        self._api_interface = api_interface

    async def _set_player_settings(self, guild: discord.Guild, player: lavalink.Player) -> None:
        guild_data = await self._config.guild(guild).all()
        player.repeat = guild_data["repeat"]
        player.shuffle = guild_data["shuffle"]
        player.shuffle_bumped = guild_data["shuffle_bumped"]
        volume = guild_data["volume"]
        if player.volume != volume:
            await player.set_volume(volume)

    async def _enqueue_tracks(self, query: str, player: lavalink.Player, requester: discord.Member, enqueue: bool = True):
        settings = await self._config.guild(player.guild).all()
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
                        "red_audio_track_enqueue", player.guild, track, requester
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
                        "red_audio_track_enqueue", player.guild, track, requester
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
                        "red_audio_track_enqueue", player.guild, single_track, requester
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
                        "red_audio_track_enqueue", player.guild, single_track, requester
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
        autoplay = await self._config.guild(player.guild).auto_play()
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
        self._bot.dispatch("red_audio_track_skip", player.guild, player.current, requester)
        await player.play()
        player.queue += queue_to_append

    async def get_tracks(self, query: str, guild: discord.Guild, local_folder: pathlib.Path = None):
        """Queries the local apis for a track and falls back to lavalink if none was found
        Note: falling back to lavalink is only possible if the bot is connected to a voice channel

        Parameters
        ----------
        query: str
            The query to search for. Supports everything core audio supports
        guild: discord.Guild
            The guild for which tracks should be returned
        local_folder: pathlib.Path
            Local folder if track is a local track
        Returns
        -------
        List[lavalink.Track], playlist_data
        """
        query = Query.process_input(query, local_folder)
        if not query.valid:
            raise InvalidQuery(f"No results found for {query}")

        player = Audio.get_player(guild)

        try:
            result, called_api = await self._api_interface.fetch_track(
                guild.id, player, query
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
        guild: discord.Guild = requester.guild
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not currently connected to a voice channel")

        await self._set_player_settings(requester.guild, player)

        tracks, playlist_data = await self._enqueue_tracks(query, player, requester)

        return tracks, playlist_data

    async def pause(self, guild: discord.Guild) -> None:
        """Pauses the player in a guild

        Parameters
        ----------
        guild: discord.Guild
            The guild in which the player should be paused
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not currently connected to a voice channel")

        if not player.paused:
            await player.pause()
            self._bot.dispatch(
                "red_audio_audio_paused", guild, True
            )

    async def resume(self, guild: discord.Guild) -> None:
        """Resumes the player in a guild

        Parameters
        ----------
        guild: discord.Guild
            The guild in which the player should be paused
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not currently connected to a voice channel")

        if player.paused:
            await player.pause(False)
            self._bot.dispatch(
                "red_audio_audio_paused", guild, False
            )

    async def current(self, guild: discord.Guild) -> Optional[lavalink.Track]:
        """Returns the current track in the given guild

        Parameters
        ----------
        guild: discord.Guild
            The guild for which the current song should be returned
        Returns
        -------
        Optional[lavalink.Track]
            The current track
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.current
        except (KeyError, IndexError):
            return None

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
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(requester.guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not connected to a voice channel")

        await self._skip(player, requester, skip_to_track)

    async def stop(self, guild: discord.Guild) -> None:
        """Stop the playback

        Parameters
        ----------
        guild: discord.Guild
            The guild in which playback should be stopped
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            player.queue = []
            player.store("playing_song", None)
            player.store("prev_requester", None)
            player.store("prev_song", None)
            player.store("requester", None)
            player.store("autoplay_notified", False)
            await player.stop()

            self._bot.dispatch("red_audio_audio_stop", guild)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Nothing playing")

    async def connect(self, channel: discord.VoiceChannel, deafen: bool = None) -> None:
        """Connect to a voice channel

        Parameters
        ----------
        channel: discord.VoiceChannel
            The channel to connect to
        deafen: bool
            Whether or not the bot should deafen on connect. Defaults to the
            guild default value if not given
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        if deafen is None:
            deafen = await self._config.guild(channel.guild).auto_deafen()

        try:
            player = lavalink.get_player(channel.guild.id)
            await player.connect(deafen=deafen, channel=channel)
        except (KeyError, IndexError):
            await lavalink.connect(channel=channel, deafen=deafen)

        if IS_DEBUG:
            log_player.debug(f"Connected to {channel} in {channel.guild}")

    async def move_to(self, channel: discord.VoiceChannel) -> None:
        """Move the player to another voice channel

        Parameters
        ----------
        channel: discord.VoiceChannel
            The channel to move the player to
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(channel.guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Not currently connected to a voice channel in the given guild")

        await player.move_to(channel)

    def is_playing(self, guild: discord.Guild):
        """Check whether the player is playing in a guild

        Parameters
        ----------
        guild: discord.Guild
            The guild to check in
        Returns
        -------
        bool
            the current playing state"""

        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.is_playing
        except (KeyError, IndexError):
            return False

    def is_connected(self, guild: discord.Guild = None) -> Optional[discord.VoiceChannel]:
        """Check whether the player is connected to a channel

        Parameters
        ----------
        guild: discord.Guild
            guild to check the connection state for
        Returns
        -------
        Optional[discord.VoiceChannel]
            discord.VoiceChannel if connected in the given guild else None
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.channel
        except (KeyError, IndexError):
            pass
        return None

    async def disconnect(self, guild: discord.Guild) -> None:
        """Disconnect the player

        Parameters
        ----------
        guild: discord.Guild
            The guild in which the player should disconnect
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            channel = player.channel

            player.queue = []
            player.store("playing_song", None)
            player.store("autoplay_notified", False)
            await player.stop()
            await player.disconnect()

            if IS_DEBUG:
                log_player.debug(f"Disconnected from {channel} in {guild}")
        except (KeyError, IndexError):
            raise NotConnectedToVoice(f"Bot is not connected to a voice channel in guild {guild}")

    async def get_volume(self, guild: discord.Guild) -> Optional[int]:
        """Get the current player volume

        Parameters
        ----------
        guild: discord.Guild
            The guild for which the volume should be returned
        Returns
        -------
        int
            The current volume
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.volume
        except (KeyError, IndexError):
            return await self._config.guild(guild).volume()

    async def set_volume(self, guild: discord.Guild, vol: int) -> int:
        """Set the player's volume

        Parameters
        ----------
        guild: discord.Guild
            The guild for which the volume should be set
        Returns
        -------
        int
            the volume after change
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        if vol < 0 or vol > 150:
            raise ValueError("Volume is not within the allowed range")

        await self._config.guild(guild).volume.set(vol)

        try:
            player = lavalink.get_player(guild.id)
            await player.set_volume(vol)
        except (KeyError, IndexError):
            pass

    async def get_queue(self, guild: discord.Guild) -> List[lavalink.Track]:
        """Get the current player queue

        Parameters
        ----------
        guild: discord.Guild
            The guild for which the queue should be returned
        Returns
        -------
        List[lavalink.Track]
            the current queue
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.queue
        except (KeyError, IndexError):
            return []

    async def set_queue(self, guild: discord.Guild, queue: List) -> None:
        """Set the player's queue

        Parameters
        ----------
        guild: discord.Guild
            The guild for which the queue should be set
        """
        if not self._lavalink.is_connected:
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            player.queue = queue
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not currently connected to a voice channel in the given guild")
