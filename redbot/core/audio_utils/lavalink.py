import asyncio
import logging
import lavalink
from typing import ClassVar

from redbot.core.utils import AsyncIter
from redbot.core import data_manager, Config
from redbot.core.bot import Red

from .api_interface import AudioAPIInterface
from .server_manager import ServerManager
from .errors import LavalinkDownloadFailed

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
    async def start(cls, bot, force_restart_ll_server: bool = False, timeout: int = 50, max_retries: int = 5) -> None:
        cls._lavalink_connection_aborted = False
        cls._bot = bot
        configs = await Config.get_conf(None, identifier=2711759130, cog_name="Audio").all()

        if force_restart_ll_server:
            await ServerManager.shutdown()
            AudioAPIInterface.close()

        if not AudioAPIInterface.is_connected():
            await AudioAPIInterface.initialize()

        async for _ in AsyncIter(range(0, max_retries)):
            external = configs["use_external_lavalink"] if "use_external_lavalink" in configs.keys() else default_config["use_external_lavalink"]
            java_exc = configs["java_exc_path"] if "java_exc_path" in configs.keys() else default_config["java_exc_path"]
            if not external:
                host = "localhost"
                password = "youshallnotpass"
                ws_port = 2333

                if not ServerManager.is_running():
                    try:
                        await ServerManager.start(java_exc)
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
                log.debug("Lavalink connection established")
            except asyncio.TimeoutError:
                log.error("Connecting to Lavalink server timed out, retrying...")
                if not external and ServerManager.is_running():
                    await ServerManager.shutdown()
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

        #ToDo restore players
        #cls._restore_task = asyncio.create_task()


    @classmethod
    async def shutdown(cls, bot, shutdown_ll_server: bool = False):
        await lavalink.close(bot)
        AudioAPIInterface.close()
        if shutdown_ll_server and ServerManager.is_running():
            await ServerManager.shutdown()
        cls._lavalink_running = False
        log.debug("Lavalink connection closed")

    @classmethod
    def is_connected(cls):
        return bool(lavalink.node._nodes)
