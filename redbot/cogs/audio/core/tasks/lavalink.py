import asyncio
from pathlib import Path

import lavalink
from red_commons.logging import getLogger

from redbot.core import data_manager
from redbot.core.i18n import Translator
from ...errors import (
    LavalinkDownloadFailed,
    InvalidArchitectureException,
    ManagedLavalinkNodeException,
)
from ...manager import ServerManager
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ...utils import task_callback_debug

log = getLogger("red.cogs.Audio.cog.Tasks.lavalink")
_ = Translator("Audio", Path(__file__))


class LavalinkTasks(MixinMeta, metaclass=CompositeMetaClass):
    def lavalink_restart_connect(self, manual: bool = False) -> None:
        lavalink.unregister_event_listener(self.lavalink_event_handler)
        lavalink.unregister_update_listener(self.lavalink_update_handler)
        if self.lavalink_connect_task:
            self.lavalink_connect_task.cancel()
        if self._restore_task:
            self._restore_task.cancel()

        self._restore_task = None
        lavalink.register_event_listener(self.lavalink_event_handler)
        lavalink.register_update_listener(self.lavalink_update_handler)
        self.lavalink_connect_task = self.bot.loop.create_task(self.lavalink_attempt_connect(manual=manual))
        self.lavalink_connect_task.add_done_callback(task_callback_debug)

    async def lavalink_attempt_connect(self, timeout: int = 50, manual: bool = False) -> None:
        self.lavalink_connection_aborted = False
        max_retries = 5
        retry_count = 0
        if lavalink.node._nodes:
            await lavalink.node.disconnect()
        if manual:
            await asyncio.sleep(5)
        while retry_count < max_retries:
            configs = await self.config.all()
            external = configs["use_external_lavalink"]
            java_exec = configs["java_exc_path"]
            if self.managed_node_controller is not None:
                await self.managed_node_controller.shutdown()
            if external is False:
                # Change these values to use whatever is set on the YAML
                host = configs["yaml"]["server"]["address"]
                port = configs["yaml"]["server"]["port"]
                password = configs["yaml"]["lavalink"]["server"]["password"]
                secured = False
                self.managed_node_controller = ServerManager(self.config)
                try:
                    await self.managed_node_controller.start(java_exec)
                except LavalinkDownloadFailed as exc:
                    await asyncio.sleep(1)
                    if exc.should_retry:
                        log.exception(
                            "Exception whilst starting managed Lavalink node, retrying...\n%s",
                            exc.response,
                        )
                        retry_count += 1
                        continue
                    else:
                        log.critical(
                            "Fatal exception whilst starting managed Lavalink node, "
                            "aborting...\n%s",
                            exc.response,
                        )
                        self.lavalink_connection_aborted = True
                        return
                except InvalidArchitectureException:
                    log.critical(
                        "Invalid machine architecture, cannot run a managed Lavalink node."
                    )
                    self.lavalink_connection_aborted = True
                    return
                except ManagedLavalinkNodeException as exc:
                    log.critical(
                        exc,
                    )
                    self.lavalink_connection_aborted = True
                    return
                except Exception as exc:
                    log.exception(
                        "Unhandled exception whilst starting managed Lavalink node, "
                        "aborting...",
                        exc_info=exc,
                    )
                    self.lavalink_connection_aborted = True
                    return
                else:
                    break
            else:
                host = configs["host"]
                password = configs["password"]
                port = configs["ws_port"]
                secured = configs["secured_ws"]
                break
        else:
            log.critical(
                "Setting up the managed Lavalink node failed after multiple attempts. "
                "See above logs for details."
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
                    ws_port=port,
                    timeout=timeout,
                    resume_key=f"Red-Core-Audio-{self.bot.user.id}-{data_manager.instance_name}",
                    secured=secured
                )
            except asyncio.TimeoutError:
                log.warning("Connecting to Lavalink node timed out, retrying...")
                if external is False and self.managed_node_controller is not None:
                    await self.managed_node_controller.shutdown()
                retry_count += 1
                await asyncio.sleep(1)  # prevent busylooping
            except Exception as exc:
                log.exception(
                    "Unhandled exception whilst connecting to Lavalink node, aborting...",
                    exc_info=exc,
                )
                self.lavalink_connection_aborted = True
                return
            else:
                break
        else:
            self.lavalink_connection_aborted = True
            log.critical(
                "Connecting to the Lavalink node failed after multiple attempts. "
                "See above tracebacks for details."
            )
            return
        if external:
            await asyncio.sleep(5)
        self._restore_task = asyncio.create_task(self.restore_players())
        self._restore_task.add_done_callback(task_callback_debug)
