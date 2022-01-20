import asyncio
import logging
import lavalink

from redbot.core.utils import AsyncIter
from redbot.core import data_manager
from redbot.core.audio_utils.audio_logging import IS_DEBUG

from .errors import LavalinkDownloadFailed, PortAlreadyInUse
from .api_utils import rgetattr

log = logging.getLogger("red.core.audio.lavalink")

default_config = {"use_external_lavalink": False, "java_exc_path": "java"}


class Lavalink:
    def __init__(self, bot, config, server_manager, api_interface):
        self._lavalink_connection_aborted: bool = False
        self._lavalink_running: bool = False
        self._bot = bot
        self._config = config
        self._server_manager = server_manager
        self._api_interface = api_interface

    @property
    def is_connected(self):
        return bool(lavalink.node._nodes)

    async def start(self, timeout: int = 50, max_retries: int = 5) -> None:
        self._lavalink_connection_aborted = False
        configs = await self._config.all()

        async for _ in AsyncIter(range(0, max_retries)):
            external = configs["use_external_lavalink"]
            java_exc = configs["java_exc_path"]
            if not external:
                host = "localhost"
                password = "youshallnotpass"
                ws_port = 2333

                if not self._server_manager.is_running:
                    try:
                        await self._server_manager.start_ll_server(java_exc)
                        self._lavalink_running = True
                    except PortAlreadyInUse:
                        log.warning(
                            "The default lavalink port seems to be in use already. "
                            "Attempting to connect to an existing server..."
                        )
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
                            self._lavalink_connection_aborted = True
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
                        self._lavalink_connection_aborted = True
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
            self._lavalink_connection_aborted = True
            return

        async for _ in AsyncIter(range(0, max_retries)):
            if lavalink.node._nodes:
                await lavalink.node.disconnect()
            try:
                await lavalink.initialize(
                    bot=self._bot,
                    host=host,
                    password=password,
                    ws_port=ws_port,
                    timeout=timeout,
                    resume_key=f"Red-Core-Audio-{self._bot.user.id}-{data_manager.instance_name}",
                )
                if IS_DEBUG:
                    log.debug("Lavalink connection established")
            except asyncio.TimeoutError:
                log.error("Connecting to Lavalink server timed out, retrying...")
                if not external and self._server_manager.is_running:
                    await self._server_manager.shutdown_ll_server()
                await asyncio.sleep(1)
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to Lavalink, aborting...", exc_info=exc
                )
                self._lavalink_connection_aborted = True
                raise
            else:
                break
        else:
            self._lavalink_connection_aborted = True
            log.critical(
                "Connecting to the Lavalink server failed after multiple attempts. "
                "See above tracebacks for details."
            )
            return
        if external:
            await asyncio.sleep(5)

        lavalink.register_event_listener(self.lavalink_event_handler)

        self._bot.dispatch("red_lavalink_connection_established", host, password, ws_port)

    async def shutdown(self):
        lavalink.unregister_event_listener(self.lavalink_event_handler)
        await lavalink.close(self._bot)
        self._lavalink_running = False
        if IS_DEBUG:
            log.debug("Lavalink connection closed")

    async def cleanup_after_error(self, player, current_track):
        while current_track in player.queue:
            player.queue.remove(current_track)

        repeat = await self._config.guild(player.channel.guild).repeat()

        if repeat:
            player.current = None

        await player.skip()

    async def lavalink_event_handler(
        self, player: lavalink.Player, event_type: lavalink.LavalinkEvents, extra
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
            self._bot.dispatch("red_audio_audio_disconnect", guild)
            return

        current_requester = rgetattr(current_track, "requester", None)
        prev_song: lavalink.Track = player.fetch("prev_song")

        if event_type == lavalink.LavalinkEvents.TRACK_START:
            # extra being a lavalink.Track object
            playing_song = player.fetch("playing_song")
            requester = player.fetch("requester")
            player.store("prev_song", playing_song)
            player.store("prev_requester", requester)
            player.store("playing_song", current_track)
            player.store("requester", current_requester)

            self._bot.dispatch("red_audio_track_start", guild, current_track, current_requester)

            if current_track:
                await self._api_interface._persistent_queue_api.played(
                    guild_id=guild.id, track_id=current_track.track_identifier
                )

        if event_type == lavalink.LavalinkEvents.TRACK_END:
            # extra being a lavalink.TrackEndReason object
            prev_requester = player.fetch("prev_requester")
            self._bot.dispatch("red_audio_track_end", guild, prev_song, prev_requester, extra)
            player.store("resume_attempts", 0)

            if self._api_interface:
                await self._api_interface._local_cache_api.youtube.clean_up_old_entries()
                await asyncio.sleep(5)
                await self._api_interface._persistent_queue_api.drop(guild.id)
                await asyncio.sleep(5)
                await self._api_interface._persistent_queue_api.delete_scheduled()

        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            # extra being None
            prev_requester = player.fetch("prev_requester")
            self._bot.dispatch("red_audio_queue_end", guild, prev_song, prev_requester)

            if self._api_interface:
                await self._api_interface._local_cache_api.youtube.clean_up_old_entries()
                await asyncio.sleep(5)
                await self._api_interface._persistent_queue_api.drop(guild.id)
                await asyncio.sleep(5)
                await self._api_interface._persistent_queue_api.delete_scheduled()

        if event_type == lavalink.LavalinkEvents.TRACK_EXCEPTION:
            # extra being an error string
            prev_requester = player.fetch("prev_requester")
            await self.cleanup_after_error(player, current_track)
            self._bot.dispatch(
                "red_audio_track_exception", guild, prev_song, prev_requester, extra
            )

        if event_type == lavalink.LavalinkEvents.TRACK_STUCK:
            # extra being the threshold in ms that the track has been stuck for
            prev_requester = player.fetch("prev_requester")
            await self.cleanup_after_error(player, current_track)
            self._bot.dispatch("red_audio_track_stuck", guild, prev_song, prev_requester, extra)

        if event_type == lavalink.LavalinkEvents.WEBSOCKET_CLOSED:
            self._bot.dispatch("red_lavalink_websocket_closed", player, extra)
