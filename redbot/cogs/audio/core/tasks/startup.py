import logging

import lavalink

from redbot.core.data_manager import cog_data_path
from redbot.core.utils.dbtools import APSWConnectionWrapper

from ...apis.interface import AudioAPIInterface
from ...apis.playlist_wrapper import PlaylistWrapper
from ..abc import MixinMeta
from ..cog_utils import _SCHEMA_VERSION, CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks.startup")


class StartUpTasks(MixinMeta, metaclass=CompositeMetaClass):
    async def initialize(self) -> None:
        await self.bot.wait_until_red_ready()
        # Unlike most cases, we want the cache to exit before migration.
        try:
            self.db_conn = APSWConnectionWrapper(
                str(cog_data_path(self.bot.get_cog("Audio")) / "Audio.db")
            )
            self.api_interface = AudioAPIInterface(
                self.bot, self.config, self.session, self.db_conn
            )
            self.playlist_api = PlaylistWrapper(self.bot, self.config, self.db_conn)
            await self.playlist_api.init()
            await self.api_interface.initialize()
            await self.data_schema_migration(
                from_version=await self.config.schema_version(), to_version=_SCHEMA_VERSION
            )
            await self.playlist_api.delete_scheduled()
            self.lavalink_restart_connect()
            self.player_automated_timer_task = self.bot.loop.create_task(
                self.player_automated_timer()
            )
            lavalink.register_event_listener(self.lavalink_event_handler)
        except Exception as err:
            log.exception("Audio failed to start up, please report this issue.", exc_info=err)
            raise err

        self.cog_ready_event.set()
