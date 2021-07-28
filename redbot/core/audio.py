import logging
import discord
import lavalink
import aiohttp
import json
import pathlib
import time

from typing import Optional, Mapping, ClassVar, List, Union

from .audio_utils import Lavalink, AudioAPIInterface, ServerManager

from .audio_utils.errors import AudioError, LavalinkNotReady, NotConnectedToVoice, InvalidQuery, NoMatchesFound
from .audio_utils.audio_dataclasses import Query, _PARTIALLY_SUPPORTED_MUSIC_EXT

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter
from redbot.core.data_manager import cog_data_path
from redbot.core.audio_utils.copied.audio_logging import IS_DEBUG

from redbot.core.audio_utils.copied.utils import CacheLevel, PlaylistScope

log = logging.getLogger("red.core.audio")

global _used_by

_used_by = []
_config = None
_bot = None

async def initialize(
        bot,
        cog_name: str,
        identifier: int,
        force_restart_ll_server: bool = False,
        force_reset_db_connection: bool = False,
) -> None:
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
    """
    global _config
    global _used_by
    global _bot
    _bot = bot
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

    if force_restart_ll_server:
        if ServerManager.is_running:
            await ServerManager.shutdown(bot)

    if force_reset_db_connection:
        if AudioAPIInterface.is_connected():
            AudioAPIInterface.close()

    if not AudioAPIInterface.is_connected():
        await AudioAPIInterface.initialize()

    if not Lavalink.is_connected():
        await Lavalink.start(bot)

    if not _used_by:
        await Player._initialize(bot)

    _used_by.append((cog_name, identifier))

async def stop(
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

    if not (cog_name, identifier) in _used_by:
        raise KeyError(f"{cog_name}: {identifier} doesn't match any established connection")

    _used_by.remove((cog_name, identifier))

    if not _used_by:
        if ServerManager.is_running:
            await ServerManager.shutdown(bot)

        if AudioAPIInterface.is_connected():
            AudioAPIInterface.close()

        if Lavalink.is_connected():
            await Lavalink.shutdown(bot)

def get_player(guild: discord.Guild) -> Optional[lavalink.Player]:
    """Returns the lavalink player object for a guild

    Parameters
    ----------
    guild: discord.Guild
        The guild for which the player should be returned
    Returns
    -------
    Optional[lavalink.Player]
        The Player object of the given guild"""
    if not Lavalink.is_connected():
        raise LavalinkNotReady("Connection to Lavalink has not yet been established")

    try:
        return lavalink.get_player(guild.id)
    except (KeyError, IndexError):
        return None

class Player:
    @classmethod
    async def _initialize(cls, bot):
        cls._log: ClassVar[logging.Logger] = logging.getLogger("red.core.audio.player")
        cls._bot: ClassVar[Red] = bot
        cls._local_folder_current_path: ClassVar[Optional[pathlib.Path]] = None
        cls._session: ClassVar[aiohttp.ClientSession] = aiohttp.ClientSession(json_serialize=json.dumps)
        cls._api_interface: ClassVar[AudioAPIInterface] = AudioAPIInterface

    @classmethod
    async def _set_player_settings(cls, guild: discord.Guild, player: lavalink.Player) -> None:
        guild_data = await _config.guild(guild).all()
        player.repeat = guild_data["repeat"]
        player.shuffle = guild_data["shuffle"]
        player.shuffle_bumped = guild_data["shuffle_bumped"]
        volume = guild_data["volume"]
        if player.volume != volume:
            await player.set_volume(volume)

    @classmethod
    async def _enqueue_tracks(cls, query, player: lavalink.Player, requester: discord.Member, enqueue: bool = True):
        settings = await _config.guild(player.guild).all()
        settings["maxlength"] = 0 if not "maxlength" in settings.keys() else settings["maxlength"]

        first_track_only = False
        index = None
        playlist_data = None
        playlist_url = None
        seek = 0
        if not isinstance(query, list):
            if query.single_track:
                first_track_only = True
                index = query.track_index
                if query.start_time:
                    seek = query.start_time

            try:
                result, called_api = await AudioAPIInterface.fetch_track(
                    requester, requester.id, player, query
                )
            except KeyError:
                raise NoMatchesFound("No matches could be found for the given query")
                pass

            tracks = result.tracks
            playlist_data = result.playlist_info
            if not enqueue:
                return tracks, None
            if not tracks:
                if result.exception_message:
                    if "Status Code" in result.exception_message:
                        cls._log.debug(result.exception_message[:2000])
                    else:
                        cls._log.debug(result.exception_message[:2000].replace("\n", ""))
                if await _config.use_external_lavalink() and query.is_local:
                    cls._log.debug("Local track")
                elif query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                    cls._log.debug("Semi supported file extension: Track might not be fully playable")
                return

        else:
            tracks = query

        if not first_track_only and len(tracks) > 1:
            if len(player.queue) >= 10000:
                cls._log.debug("Queue limit reached")
            track_len = 0
            empty_queue = not player.queue
            async for track in AsyncIter(tracks):
                if len(player.queue) >= 10000:
                    cls._log.debug("Queue limit reached")
                    break
                query = Query.process_input(track, cls._local_folder_current_path)

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
                    cls._bot.dispatch(
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
                    cls._bot.dispatch(
                        "red_audio_track_enqueue", player.guild, track, requester
                    )
            player.maybe_shuffle(0 if empty_queue else 1)

            if len(tracks) > track_len:
                cls._log.debug(f"{len(tracks) - track_len} tracks cannot be enqueued")

            if not player.current:
                await player.play()
            return tracks, playlist_data

        else:
            try:
                if len(player.queue) >= 10000:
                    cls._log.debug("Queue limit reached")

                single_track = (
                    tracks if isinstance(tracks, lavalink.rest_api.Track)
                    else tracks[index] if index else tracks[0]
                )

                if seek and seek > 0:
                    single_track.start_timestamp = seek * 1000

                if settings["maxlength"] > 0:
                    player.add(requester, single_track)
                    cls._bot.dispatch(
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
                    cls._bot.dispatch(
                        "red_audio_track_enqueue", player.guild, single_track, requester
                    )
                    player.maybe_shuffle()
            except IndexError:
                raise InvalidQuery(f"No results found for {query}")
            except Exception as e:
                raise e

        if not player.current:
            cls._log.debug("Starting player")
            await player.play()
        return single_track, None

    @classmethod
    async def _skip(cls, player: lavalink.Player, requester: Union[discord.User, discord.Member], skip_to_track: int = None) -> None:
        autoplay = await _config.guild(player.guild).auto_play()
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
        cls._bot.dispatch("red_audio_track_skip", player.guild, player.current, requester)
        await player.play()
        player.queue += queue_to_append

    @classmethod
    async def play(cls, query: str, requester: discord.Member, local_folder: pathlib.Path = None):
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
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        query = Query.process_input(query, local_folder)
        try:
            player = lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not currently connected to a voice channel")

        await cls._set_player_settings(requester.guild, player)

        if not query.valid:
            raise InvalidQuery(f"No results found for {query}")

        tracks, playlist_data = await cls._enqueue_tracks(query, player, requester)

        return tracks, playlist_data

    @classmethod
    async def pause(cls, guild: discord.Guild) -> None:
        """Pauses the player in a guild

        Parameters
        ----------
        guild: discord.Guild
            The guild in which the player should be paused
        """
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not currently connected to a voice channel")

        if not player.paused:
            await player.pause()
            cls._bot.dispatch(
                "red_audio_audio_paused", guild, True
            )

    @classmethod
    async def resume(cls, guild: discord.Guild) -> None:
        """Resumes the player in a guild

        Parameters
        ----------
        guild: discord.Guild
            The guild in which the player should be paused
        """
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not currently connected to a voice channel")

        if player.paused:
            await player.pause(False)
            cls._bot.dispatch(
                "red_audio_audio_paused", guild, False
            )

    @classmethod
    async def current(cls, guild: discord.Guild) -> Optional[lavalink.Track]:
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
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.current
        except (KeyError, IndexError):
            return None

    @classmethod
    async def queue(cls, guild: discord.Guild) -> List[lavalink.Track]:
        """Returns the player's queue in the given guild

        Parameters
        ----------
        guild: discord.Guild
            The guild for which the queue should be returned
        Returns
        -------
        List[lavalink.Track]
            The current queue
        """
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.queue
        except (KeyError, IndexError):
            return []

    @classmethod
    async def skip(cls,
                   requester: discord.Member,
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
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(requester.guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Bot is not connected to a voice channel")

        await cls._skip(player, requester, skip_to_track)

    @classmethod
    async def stop(cls, guild: discord.Guild) -> None:
        """Stop the playback

        Parameters
        ----------
        guild: discord.Guild
            The guild in which playback should be stopped
        """
        if not Lavalink.is_connected():
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

            cls._bot.dispatch("red_audio_audio_stop", guild)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Nothing playing")

    @classmethod
    async def connect(cls, channel: discord.VoiceChannel, deafen: bool = None) -> None:
        """Connect to a voice channel

        Parameters
        ----------
        channel: discord.VoiceChannel
            The channel to connect to
        deafen: bool
            Whether or not the bot should deafen on connect. Defaults to the
            guild default value if not given
        """
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        if deafen is None:
            deafen = await _config.guild(channel.guild).auto_deafen()

        try:
            player = lavalink.get_player(channel.guild.id)
            await player.connect(deafen=deafen, channel=channel)
        except (KeyError, IndexError):
            await lavalink.connect(channel=channel, deafen=deafen)

        if IS_DEBUG:
            cls._log.debug(f"Connected to {channel} in {channel.guild}")

    @classmethod
    async def move_to(cls, channel: discord.VoiceChannel) -> None:
        """Move the player to another voice channel

        Parameters
        ----------
        channel: discord.VoiceChannel
            The channel to move the player to
        """
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(channel.guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Not currently connected to a voice channel in the given guild")

        await player.move_to(channel)

    @classmethod
    def is_playing(cls, guild: discord.Guild):
        """Check whether the player is playing in a guild

        Parameters
        ----------
        guild: discord.Guild
            The guild to check in
        Returns
        -------
        bool
            the current playing state"""

        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.is_playing
        except (KeyError, IndexError):
            return False

    @classmethod
    def is_connected(cls, channel: discord.VoiceChannel) -> bool:
        """Check whether the player is connected to a channel

        Parameters
        ----------
        channel: discord.VoiceChannel
            The query to search for. Supports everything core audio supports
        Returns
        -------
        bool
            the current connection state
        """
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(channel.guild.id)
            if player.channel == channel:
                return True
        except (KeyError, IndexError):
            return False
        return False

    @classmethod
    async def disconnect(cls, guild: discord.Guild) -> None:
        """Disconnect the player

        Parameters
        ----------
        guild: discord.Guild
            The guild in which the player should disconnect
        """
        if not Lavalink.is_connected():
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
                cls._log.debug(f"Disconnected from {channel} in {guild}")
        except (KeyError, IndexError):
            raise NotConnectedToVoice(f"Bot is not connected to a voice channel in guild {guild}")

    @classmethod
    async def get_volume(cls, guild: discord.Guild) -> Optional[int]:
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
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        try:
            player = lavalink.get_player(guild.id)
            return player.volume
        except (KeyError, IndexError):
            return await _config.guild(guild).volume()

    @classmethod
    async def set_volume(cls, guild: discord.Guild, vol: int) -> int:
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
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        if vol < 0 or vol > 150:
            raise ValueError("Volume is not within the allowed range")

        await _config.guild(guild).volume.set(vol)

        try:
            player = lavalink.get_player(guild.id)
            await player.set_volume(vol)
        except (KeyError, IndexError):
            pass