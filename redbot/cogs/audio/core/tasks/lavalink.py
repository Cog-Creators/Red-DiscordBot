import asyncio
import logging
from pathlib import Path

import lavalink

from redbot.core.i18n import Translator
from ...errors import LavalinkDownloadFailed
from ...manager import ServerManager
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks.lavalink")
_ = Translator("Audio", Path(__file__))


class LavalinkTasks(MixinMeta, metaclass=CompositeMetaClass):
    def lavalink_restart_connect(self) -> None:
        if self.lavalink_connect_task:
            self.lavalink_connect_task.cancel()

        self.lavalink_connect_task = self.bot.loop.create_task(self.lavalink_attempt_connect())

    async def lavalink_attempt_connect(self, timeout: int = 50) -> None:
        self.lavalink_connection_aborted = False
        max_retries = 5
        retry_count = 0
        while retry_count < max_retries:
            configs = await self.config.all()
            external = configs["use_external_lavalink"]
            java_exec = configs["java_exc_path"]
            if external is False:
                settings = self._default_lavalink_settings
                host = settings["host"]
                password = settings["password"]
                rest_port = settings["rest_port"]
                ws_port = settings["ws_port"]
                if self.player_manager is not None:
                    await self.player_manager.shutdown()
                self.player_manager = ServerManager()
                try:
                    await self.player_manager.start(java_exec)
                except LavalinkDownloadFailed as exc:
                    await asyncio.sleep(1)
                    if exc.should_retry:
                        log.exception(
                            "Exception whilst starting internal Lavalink server, retrying...",
                            exc_info=exc,
                        )
                        retry_count += 1
                        continue
                    else:
                        log.exception(
                            "Fatal exception whilst starting internal Lavalink server, "
                            "aborting...",
                            exc_info=exc,
                        )
                        self.lavalink_connection_aborted = True
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
                    self.lavalink_connection_aborted = True
                    raise
                else:
                    break
            else:
                host = configs["host"]
                password = configs["password"]
                rest_port = configs["rest_port"]
                ws_port = configs["ws_port"]
                break
        else:
            log.critical(
                "Setting up the Lavalink server failed after multiple attempts. "
                "See above tracebacks for details."
            )
            self.lavalink_connection_aborted = True
            return

        retry_count = 0
        while retry_count < max_retries:
            try:
                await lavalink.initialize(
                    bot=self.bot,
                    host=host,
                    password=password,
                    rest_port=rest_port,
                    ws_port=ws_port,
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                log.error("Connecting to Lavalink server timed out, retrying...")
                if external is False and self.player_manager is not None:
                    await self.player_manager.shutdown()
                retry_count += 1
                await asyncio.sleep(1)  # prevent busylooping
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to Lavalink, aborting...", exc_info=exc
                )
                self.lavalink_connection_aborted = True
                raise
            else:
                break
        else:
            self.lavalink_connection_aborted = True
            log.critical(
                "Connecting to the Lavalink server failed after multiple attempts. "
                "See above tracebacks for details."
            )
