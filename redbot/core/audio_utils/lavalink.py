import asyncio
import logging
import lavalink
import functools
from typing import ClassVar, Any

from redbot.core.utils import AsyncIter
from redbot.core import data_manager, audio
from redbot.core.bot import Red
from redbot.core.audio_utils.copied.audio_logging import IS_DEBUG

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

        #ToDo restore players
        #cls._restore_task = asyncio.create_task()

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