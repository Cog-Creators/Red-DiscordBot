import logging
import discord
import lavalink
import aiohttp
import json
import pathlib
import time

from typing import Optional, Mapping, ClassVar

from .audio_utils import Lavalink, ServerManager, AudioAPIInterface
from .audio_utils.errors import AudioError
from .audio_utils.audio_dataclasses import Query, _PARTIALLY_SUPPORTED_MUSIC_EXT

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import escape

from redbot.core.audio_utils.copied.utils import CacheLevel, PlaylistScope
#from redbot.cogs.audio.apis.interface import AudioAPIInterface

log = logging.getLogger("red.core.audio")
_used_by = []

class LavalinkNotReady(AudioError):
    """LavaLink server is not ready"""

class NotConnectedToVoice(AudioError):
    """Bot is not connected to a voice channel"""

class InvalidQuery(AudioError):
    """Query is invalid - No tracks found"""

async def initialize(
        bot,
        cog_name: str,
        identifier: int,
        force_restart_ll_server: bool = False,
        force_reset_db_connection: bool = False,
) -> None:
    """Initializes the api and established the connection to lavalink

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
    None
    """

    _used_by.append((cog_name, identifier))

    if force_restart_ll_server:
        if ServerManager.is_running():
            await ServerManager.shutdown()

    if force_reset_db_connection:
        if AudioAPIInterface.is_connected():
            AudioAPIInterface.close()

    if not AudioAPIInterface.is_connected():
        await AudioAPIInterface.initialize()

    if not Lavalink.is_connected():
        await Lavalink.start(bot)

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
    Returns
    -------
    None
    """

    if not (cog_name, identifier) in _used_by:
        raise KeyError(f"{cog_name}: {identifier} doesn't match any established connection")

    _used_by.remove((cog_name, identifier))

    if not _used_by:
        if ServerManager.is_running():
            await ServerManager.shutdown()

        if AudioAPIInterface.is_connected():
            AudioAPIInterface.close()

        if Lavalink.is_connected():
            await Lavalink.shutdown(bot)

class Player:
    _log: ClassVar[logging.Logger] = logging.getLogger("red.core.audio.player")
    _bot: ClassVar[Red] = Lavalink.bot()
    _local_folder_current_path: ClassVar[Optional[pathlib.Path]] = None
    _session: ClassVar[aiohttp.ClientSession] = aiohttp.ClientSession(json_serialize=json.dumps)
    _api_interface: ClassVar[AudioAPIInterface] = AudioAPIInterface

    _config: ClassVar[Config] = Config.get_conf(None, identifier=2711759130, cog_name="Audio")

    _default_lavalink_settings = {
        "host": "localhost",
        "rest_port": 2333,
        "ws_port": 2333,
        "password": "youshallnotpass",
    }

    default_global = dict(
        schema_version=1,
        bundled_playlist_version=0,
        owner_notification=0,
        cache_level=CacheLevel.all().value,
        cache_age=365,
        daily_playlists=False,
        global_db_enabled=False,
        global_db_get_timeout=5,
        status=False,
        use_external_lavalink=False,
        restrict=True,
        localpath=str(cog_data_path(raw_name="Audio")),
        url_keyword_blacklist=[],
        url_keyword_whitelist=[],
        java_exc_path="java",
        **_default_lavalink_settings,
    )

    default_guild = dict(
        auto_play=False,
        currently_auto_playing_in=None,
        auto_deafen=True,
        autoplaylist=dict(
            enabled=True,
            id=42069,
            name="Aikaterna's curated tracks",
            scope=PlaylistScope.GLOBAL.value,
        ),
        persist_queue=True,
        disconnect=False,
        dj_enabled=False,
        dj_role=None,
        daily_playlists=False,
        emptydc_enabled=False,
        emptydc_timer=0,
        emptypause_enabled=False,
        emptypause_timer=0,
        jukebox=False,
        jukebox_price=0,
        maxlength=0,
        notify=False,
        prefer_lyrics=False,
        repeat=False,
        shuffle=False,
        shuffle_bumped=True,
        thumbnail=False,
        volume=100,
        vote_enabled=False,
        vote_percent=0,
        room_lock=None,
        url_keyword_blacklist=[],
        url_keyword_whitelist=[],
        country_code="US",
    )
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

    @classmethod
    async def _set_player_settings(cls, guild: discord.Guild, player: lavalink.Player) -> None:
        player.repeat = await cls._config.guild(guild).repeat()
        player.shuffle = await cls._config.guild(guild).shuffle()
        player.shuffle_bumped = await cls._config.guild(guild).shuffle_bumped()
        volume = await cls._config.guild(guild).volume()
        if player.volume != volume:
            await player.set_volume(volume)

    @classmethod
    async def _enqueue_tracks(cls, query, player: lavalink.Player, requester: discord.Member, enqueue: bool = True):
        settings = await cls._config.guild(player.guild).all()
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
                #result, called_api = await cls._api_interface.fetch_track(ctx, player, query)
                result, called_api = await AudioAPIInterface.fetch_track(
                    requester, requester.id, player, query
                )
            except KeyError:
                cls._log.debug("No tracks found")

            tracks = result.tracks
            playlist_data = result.playlist_info
            if not enqueue:
                return tracks
            if not tracks:
                if result.exception_message:
                    if "Status Code" in result.exception_message:
                        cls._log.debug(result.exception_message[:2000])
                    else:
                        cls._log.debug(result.exception_message[:2000].replace("\n", ""))
                if await cls._config.use_external_lavalink() and query.is_local:
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
            player.maybe_shuffle(0 if empty_queue else 1)

            if len(tracks) > track_len:
                cls._log.debug(f"{len(tracks) - track_len} tracks cannot be enqueued")

            playlist_name = escape(
                playlist_data.name if playlist_data else "No Title", formatting=True
            )
            if not player.current:
                cls._log.debug("Starting player")
                await player.play()
            return tracks

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
                    player.maybe_shuffle()
            except IndexError:
                cls._log.debug("Nothing found, check your console or logs for details")
            except Exception as e:
                raise e

        if not player.current:
            cls._log.debug("Starting player")
            await player.play()
        return single_track

    @classmethod
    async def play(cls, query: str, requester: discord.Member, local_folder: pathlib.Path = None) -> None:
        guild: discord.Guild = requester.guild
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        query = Query.process_input(query, local_folder)
        try:
            player = lavalink.get_player(guild.id)
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Connect to a voice channel first")

        await cls._set_player_settings(requester.guild, player)

        if not query.valid:
            raise InvalidQuery(f"No results found for {query}")

        await cls._enqueue_tracks(query, player, requester)

    @classmethod
    async def stop(cls, guild: discord.Guild) -> None:
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
        except (KeyError, IndexError):
            raise NotConnectedToVoice("Nothing playing")

    @classmethod
    async def connect(cls, channel: discord.VoiceChannel, deafen: bool = None) -> None:
        if not Lavalink.is_connected():
            raise LavalinkNotReady("Connection to Lavalink has not yet been established")

        if deafen is None:
            deafen = await cls._config.guild(channel.guild).auto_deafen()

        try:
            player = lavalink.get_player(channel.guild.id)
            await player.connect(deafen=deafen, channel=channel)
        except (KeyError, IndexError):
            await lavalink.connect(channel=channel, deafen=deafen)

        cls._log.debug(f"Connected to {channel} in {channel.guild}")

    @classmethod
    def is_connected(cls, channel: discord.VoiceChannel) -> bool:
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
            cls._log.debug(f"Disconnected from {channel} in {guild}")
        except (KeyError, IndexError):
            raise NotConnectedToVoice(f"Bot is not connected to a voice channel in guild {guild}")

    @classmethod
    async def get_volume(cls, guild: discord.Guild) -> Optional[int]:
        try:
            player = lavalink.get_player(guild.id)
            return player.volume
        except (KeyError, IndexError):
            return await cls._config.guild(guild).volume()

    @classmethod
    async def set_volume(cls, guild: discord.Guild, vol: int) -> int:
        if vol < 0 or vol > 150:
            raise ValueError("Volume is not within the allowed range")

        await cls._config.guild(guild).volume.set(vol)

        try:
            player = lavalink.get_player(guild.id)
            await player.set_volume(vol)
        except (KeyError, IndexError):
            pass