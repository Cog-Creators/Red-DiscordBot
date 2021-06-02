import asyncio
import logging
from pathlib import Path

import lavalink

from redbot.core import data_manager
from redbot.core.i18n import Translator
from ...errors import LavalinkDownloadFailed
from ...manager import ServerManager
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks.lavalink")
_ = Translator("Audio", Path(__file__))


class LavalinkTasks(MixinMeta, metaclass=CompositeMetaClass):
    def lavalink_restart_connect(self) -> None:
        lavalink.unregister_event_listener(self.lavalink_event_handler)
        lavalink.unregister_update_listener(self.lavalink_update_handler)
        if self.lavalink_connect_task:
            self.lavalink_connect_task.cancel()
        if self._restore_task:
            self._restore_task.cancel()

        self._restore_task = None
        lavalink.register_event_listener(self.lavalink_event_handler)
        lavalink.register_update_listener(self.lavalink_update_handler)
        self.lavalink_connect_task = self.bot.loop.create_task(self.lavalink_attempt_connect())

    async def lavalink_attempt_connect(self, timeout: int = 50) -> None:
        self.lavalink_connection_aborted = False
        max_retries = 5
        retry_count = 0
        while retry_count < max_retries:
            managed = await self.config_cache.use_managed_lavalink.get_global()
            java_exec = str(await self.config_cache.java_exec.get_global())
            host = await self.config_cache.node_config.get_host(node_identifier="primary")
            password = await self.config_cache.node_config.get_password(node_identifier="primary")
            port = await self.config_cache.node_config.get_port(node_identifier="primary")
            if managed is True:
                if self.player_manager is not None:
                    await self.player_manager.shutdown()
                self.player_manager = ServerManager(host, password, port, self.config_cache)
                try:
                    await self.player_manager.start(java_exec)
                except LavalinkDownloadFailed as exc:
                    await asyncio.sleep(1)
                    if exc.should_retry:
                        log.exception(
                            "Exception whilst starting managed node, retrying...",
                            exc_info=exc,
                        )
                        retry_count += 1
                        continue
                    else:
                        log.exception(
                            "Fatal exception whilst starting managed node, aborting...",
                            exc_info=exc,
                        )
                        self.lavalink_connection_aborted = True
                        raise
                except asyncio.CancelledError:
                    log.exception(
                        "Invalid machine architecture, cannot run a managed Lavalink node."
                    )
                    raise
                except Exception as exc:
                    log.exception(
                        "Unhandled exception whilst starting managed node, aborting...",
                        exc_info=exc,
                    )
                    self.lavalink_connection_aborted = True
                    raise
                else:
                    break
            else:
                break
        else:
            log.critical(
                "Setting up the managed node failed after multiple attempts. "
                "See above tracebacks for details."
            )
            self.lavalink_connection_aborted = True
            return

        retry_count = 0
        while retry_count < max_retries:
            if lavalink.node._nodes:
                await lavalink.node.disconnect()
            try:
                await lavalink.initialize(
                    bot=self.bot,
                    host=host,
                    password=password,
                    ws_port=port,
                    timeout=timeout,
                    resume_key=f"Red-Core-Audio-{self.bot.user.id}-{data_manager.instance_name}",
                )
            except asyncio.TimeoutError:
                log.error("Connecting to node timed out, retrying...")
                if managed is True and self.player_manager is not None:
                    await self.player_manager.shutdown()
                retry_count += 1
                await asyncio.sleep(1)  # prevent busylooping
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to node, aborting...", exc_info=exc
                )
                self.lavalink_connection_aborted = True
                raise
            else:
                break
        else:
            self.lavalink_connection_aborted = True
            log.critical(
                "Connecting to the node failed after multiple attempts. "
                "See above tracebacks for details."
            )
            return
        if managed is False:
            await asyncio.sleep(5)
        self._restore_task = asyncio.create_task(self.restore_players())
