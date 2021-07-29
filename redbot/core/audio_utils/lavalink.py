import asyncio
import logging
import lavalink
import itertools
from typing import ClassVar, Any

from redbot.core.utils import AsyncIter
from redbot.core import data_manager, audio
from redbot.core.bot import Red
from redbot.core.audio_utils.copied.audio_logging import IS_DEBUG, debug_exc_log

from .api_interface import AudioAPIInterface
from .server_manager import ServerManager
from .errors import LavalinkDownloadFailed
from .api_utils import rgetattr

log = logging.getLogger("red.core.audio.lavalink")

default_config = {
    "use_external_lavalink": False,
    "java_exc_path": "java"
}

class Lavalink:
    _lavalink_connection_aborted: ClassVar[bool] = False
    _lavalink_running: ClassVar[bool] = False
    _bot: ClassVar[Red] = None

    @classmethod
    def bot(cls):
        return cls._bot

    @classmethod
    async def start(cls, bot, timeout: int = 50, max_retries: int = 5) -> None:
        cls._lavalink_connection_aborted = False
        cls._bot = bot
        configs = await audio._config.all()

        async for _ in AsyncIter(range(0, max_retries)):
            external = configs["use_external_lavalink"]
            java_exc = configs["java_exc_path"]
            if not external:
                host = "localhost"
                password = "youshallnotpass"
                ws_port = 2333

                if not ServerManager.is_running:
                    try:
                        await ServerManager.start(bot, java_exc)
                        cls._lavalink_running = True
                    except LavalinkDownloadFailed as exc:
                        await asyncio.sleep(1)
                        if exc.should_retry:
                            log.exception(
                                "Exception whilst starting internal Lavalink server, retrying...",
                                exc_info=exc,
                            )
                            continue
                        else:
                            log.exception(
                                "Fatal exception whilst starting internal Lavalink server, "
                                "aborting...",
                                exc_info=exc,
                            )
                            cls._lavalink_connection_aborted = True
                            raise
                    except asyncio.CancelledError:
                        log.exception("Invalid machine architecture, cannot run Lavalink.")
                        raise
                    except Exception as exc:
                        log.exception(
                            "Unhandled exception whilst starting internal Lavalink server, "
                            "aborting...",
                            exc_info=exc,
                        )
                        cls._lavalink_connection_aborted = True
                        raise
                    else:
                        break
                else:
                    break
            else:
                host = configs["host"]
                password = configs["password"]
                ws_port = configs["ws_port"]
                break
        else:
            log.critical(
                "Setting up the Lavalink server failed after multiple attempts. "
                "See above tracebacks for details."
            )
            cls._lavalink_connection_aborted = True
            return

        async for _ in AsyncIter(range(0, max_retries)):
            if lavalink.node._nodes:
                await lavalink.node.disconnect()
            try:
                await lavalink.initialize(
                    bot=bot,
                    host=host,
                    password=password,
                    ws_port=ws_port,
                    timeout=timeout,
                    resume_key=f"Red-Core-Audio-{bot.user.id}-{data_manager.instance_name}"
                )
                if IS_DEBUG:
                    log.debug("Lavalink connection established")
            except asyncio.TimeoutError:
                log.error("Connecting to Lavalink server timed out, retrying...")
                if not external and ServerManager.is_running:
                    await ServerManager.shutdown(bot)
                await asyncio.sleep()
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to Lavalink, aborting...", exc_info=exc
                )
                cls._lavalink_connection_aborted = True
                raise
            else:
                break
        else:
            cls._lavalink_connection_aborted = True
            log.critical(
                "Connecting to the Lavalink server failed after multiple attempts. "
                "See above tracebacks for details."
            )
            return
        if external:
            await asyncio.sleep(5)

        lavalink.register_event_listener(cls.lavalink_event_handler)

        bot.dispatch(
            "lavalink_connection_established", host, password, ws_port
        )

        # tries = 0
        # tracks_to_restore = await audio.AudioAPIInterface._persistent_queue_api.fetch_all()
        # while not lavalink.node._nodes:
        #     await asyncio.sleep(1)
        #     tries += 1
        #     if tries > 60:
        #         log.exception("Unable to restore players, couldn't connect to lavalink.")
        #         return
        # metadata = {}
        # all_guilds = await audio._config.all_guilds()
        # async for guild_id, guild_data in AsyncIter(all_guilds.items(), steps=100):
        #     if guild_data["auto_play"]:
        #         if guild_data["currently_auto_playing_in"]:
        #             notify_channel, vc_id = guild_data["currently_auto_playing_in"]
        #             metadata[guild_id] = (notify_channel, vc_id)
        #
        # for guild_id, track_data in itertools.groupby(tracks_to_restore, key=lambda x: x.guild_id):
        #     await asyncio.sleep(0)
        #     tries = 0
        #     try:
        #         player: Optional[lavalink.Player] = None
        #         track_data = list(track_data)
        #         guild = bot.get_guild(guild_id)
        #         if not guild:
        #             continue
        #         persist_cache = audio._persist_queue_cache.setdefault(
        #             guild_id, await audio._config.guild(guild).persist_queue()
        #         )
        #         if not persist_cache:
        #             await audio.AudioAPIInterface._persistent_queue_api.drop(guild_id)
        #             continue
        #         if not cls._lavalink_running:
        #             player = None
        #         else:
        #             player = audio.get_player(guild)
        #
        #         vc = 0
        #         guild_data = await audio._config.guild(guild).all()
        #         shuffle = guild_data["shuffle"]
        #         repeat = guild_data["repeat"]
        #         volume = guild_data["volume"]
        #         shuffle_bumped = guild_data["shuffle_bumped"]
        #         auto_deafen = guild_data["auto_deafen"]
        #
        #         if player is None:
        #             while tries < 5 and vc is not None:
        #                 try:
        #                     notify_channel_id, vc_id = metadata.pop(
        #                         guild_id, (None, track_data[-1].room_id)
        #                     )
        #                     vc = guild.get_channel(vc_id)
        #                     if not vc:
        #                         break
        #                     perms = vc.permissions_for(guild.me)
        #                     if not (perms.connect and perms.speak):
        #                         vc = None
        #                         break
        #                     player = await lavalink.connect(vc, deafen=auto_deafen)
        #                     player.store("notify_channel", notify_channel_id)
        #                     break
        #                 except IndexError:
        #                     await asyncio.sleep(5)
        #                     tries += 1
        #                 except Exception as exc:
        #                     tries += 1
        #                     debug_exc_log(
        #                         log, exc, "Failed to restore music voice channel %s", vc_id
        #                     )
        #                     if vc is None:
        #                         break
        #                     else:
        #                         await asyncio.sleep(1)
        #
        #         if tries >= 5 or guild is None or vc is None or player is None:
        #             await audio.AudioAPIInterface._persistent_queue_api.drop(guild_id)
        #             continue
        #
        #         player.repeat = repeat
        #         player.shuffle = shuffle
        #         player.shuffle_bumped = shuffle_bumped
        #         if player.volume != volume:
        #             await player.set_volume(volume)
        #         for track in track_data:
        #             track = track.track_object
        #             player.add(guild.get_member(track.extras.get("requester")) or guild.me, track)
        #         player.maybe_shuffle()
        #         if not player.is_playing:
        #             await player.play()
        #         log.info("Restored %r", player)
        #     except Exception as err:
        #         debug_exc_log(log, err, "Error restoring player in %d", guild_id)
        #         await audio.AudioAPIInterface._persistent_queue_api.drop(guild_id)
        #
        # for guild_id, (notify_channel_id, vc_id) in metadata.items():
        #     guild = self.bot.get_guild(guild_id)
        #     player: Optional[lavalink.Player] = None
        #     vc = 0
        #     tries = 0
        #     if not guild:
        #         continue
        #     if not cls._lavalink_running:
        #         player = None
        #     else:
        #         try:
        #             player = lavalink.get_player(guild_id)
        #         except IndexError:
        #             player = None
        #         except KeyError:
        #             player = None
        #     if player is None:
        #         guild_data = await audio._config.guild(guild).all()
        #         shuffle = guild_data["shuffle"]
        #         repeat = guild_data["repeat"]
        #         volume = guild_data["volume"]
        #         shuffle_bumped = guild_data["shuffle_bumped"]
        #         auto_deafen = guild_data["auto_deafen"]
        #
        #         while tries < 5 and vc is not None:
        #             try:
        #                 vc = guild.get_channel(vc_id)
        #                 if not vc:
        #                     break
        #                 perms = vc.permissions_for(guild.me)
        #                 if not (perms.connect and perms.speak):
        #                     vc = None
        #                     break
        #                 player = await lavalink.connect(vc, deafen=auto_deafen)
        #                 player.store("notify_channel", notify_channel_id)
        #                 break
        #             except IndexError:
        #                 await asyncio.sleep(5)
        #                 tries += 1
        #             except Exception as exc:
        #                 tries += 1
        #                 debug_exc_log(log, exc, "Failed to restore music voice channel %s", vc_id)
        #                 if vc is None:
        #                     break
        #                 else:
        #                     await asyncio.sleep(1)
        #         if tries >= 5 or guild is None or vc is None or player is None:
        #             continue
        #
        #         player.repeat = repeat
        #         player.shuffle = shuffle
        #         player.shuffle_bumped = shuffle_bumped
        #         if player.volume != volume:
        #             await player.set_volume(volume)
        #         player.maybe_shuffle()
        #         log.info("Restored %r", player)
        #         # if not player.is_playing:
        #         #     notify_channel = player.fetch("notify_channel")
        #         #     try:
        #         #         await audio.AudioAPIInterface.autoplay(player, self.playlist_api)
        #         #     except DatabaseError:
        #         #         notify_channel = self.bot.get_channel(notify_channel)
        #         #         if notify_channel:
        #         #             await self.send_embed_msg(
        #         #                 notify_channel, title=_("Couldn't get a valid track.")
        #         #             )
        #         #         return
        #         #     except TrackEnqueueError:
        #         #         notify_channel = self.bot.get_channel(notify_channel)
        #         #         if notify_channel:
        #         #             await self.send_embed_msg(
        #         #                 notify_channel,
        #         #                 title=_("Unable to Get Track"),
        #         #                 description=_(
        #         #                     "I'm unable to get a track from Lavalink at the moment, "
        #         #                     "try again in a few minutes."
        #         #                 ),
        #         #             )
        #         #         return
        # del metadata
        # del all_guilds

    @classmethod
    async def shutdown(cls, bot):
        lavalink.unregister_event_listener(cls.lavalink_event_handler)
        await lavalink.close(bot)
        cls._lavalink_running = False
        if IS_DEBUG:
            log.debug("Lavalink connection closed")

    @classmethod
    def is_connected(cls):
        return bool(lavalink.node._nodes)

    @classmethod
    async def cleanup_after_error(cls, player, current_track):
        while current_track in player.queue:
            player.queue.remove(current_track)

        repeat = await audio._config.guild(player.channel.guild).repeat()

        if repeat:
            player.current = None

        await player.skip()

    @classmethod
    async def lavalink_event_handler(
        cls,
        player: lavalink.Player,
        event_type: lavalink.LavalinkEvents,
        extra
    ) -> None:
        current_track = player.current
        current_channel = player.channel
        guild: discord.Guild = rgetattr(current_channel, "guild", None)
        if not (current_channel and guild):
            player.store("autoplay_notified", False)
            await player.stop()
            await player.disconnect()
            return
        if not guild:
            return

        if event_type == lavalink.LavalinkEvents.FORCED_DISCONNECT:
            cls._bot.dispatch("red_audio_audio_disconnect", guild)
            return

        current_requester = rgetattr(current_track, "requester", None)
        prev_song: lavalink.Track = player.fetch("prev_song")

        if event_type == lavalink.LavalinkEvents.TRACK_START:
            #extra being a lavalink.Track object
            playing_song = player.fetch("playing_song")
            requester = player.fetch("requester")
            player.store("prev_song", playing_song)
            player.store("prev_requester", requester)
            player.store("playing_song", current_track)
            player.store("requester", current_requester)

            cls._bot.dispatch("red_audio_track_start", guild, current_track, current_requester)

            if current_track:
                await audio.AudioAPIInterface._persistent_queue_api.played(
                    guild_id=guild.id, track_id=current_track.track_identifier
                )

        if event_type == lavalink.LavalinkEvents.TRACK_END:
            #extra being a lavalink.TrackEndReason object
            prev_requester = player.fetch("prev_requester")
            cls._bot.dispatch("red_audio_track_end", guild, prev_song, prev_requester, extra)
            player.store("resume_attempts", 0)

            if audio.AudioAPIInterface:
                await audio.AudioAPIInterface._local_cache_api.youtube.clean_up_old_entries()
                await asyncio.sleep(5)
                await audio.AudioAPIInterface._persistent_queue_api.drop(guild.id)
                await asyncio.sleep(5)
                await audio.AudioAPIInterface._persistent_queue_api.delete_scheduled()

        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            #extra being None
            prev_requester = player.fetch("prev_requester")
            cls._bot.dispatch("red_audio_queue_end", guild, prev_song, prev_requester)

            if audio.AudioAPIInterface:
                await audio.AudioAPIInterface._local_cache_api.youtube.clean_up_old_entries()
                await asyncio.sleep(5)
                await audio.AudioAPIInterface._persistent_queue_api.drop(guild.id)
                await asyncio.sleep(5)
                await audio.AudioAPIInterface._persistent_queue_api.delete_scheduled()

        if event_type == lavalink.LavalinkEvents.TRACK_EXCEPTION:
            #extra being an error string
            prev_requester = player.fetch("prev_requester")
            await cls.cleanup_after_error(player, current_track)
            cls._bot.dispatch("red_audio_track_exception", guild, prev_song, prev_requester, extra)

        if event_type == lavalink.LavalinkEvents.TRACK_STUCK:
            #extra being the threshold in ms that the track has been stuck for
            prev_requester = player.fetch("prev_requester")
            await cls.cleanup_after_error(player, current_track)
            cls._bot.dispatch("red_audio_track_stuck", guild, prev_song, prev_requester, extra)

        if event_type == lavalink.LavalinkEvents.WEBSOCKET_CLOSED:
            cls._bot.dispatch("lavalink_websocket_closed", player, extra)