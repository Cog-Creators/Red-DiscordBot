import asyncio
import logging
import time
from typing import Dict

import lavalink

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks.player")


class PlayerTasks(MixinMeta, metaclass=CompositeMetaClass):
    async def player_automated_timer(self) -> None:
        stop_times: Dict = {}
        pause_times: Dict = {}
        while True:
            for p in lavalink.all_players():
                server = p.channel.guild

                if [self.bot.user] == p.channel.members:
                    stop_times.setdefault(server.id, time.time())
                    pause_times.setdefault(server.id, time.time())
                else:
                    stop_times.pop(server.id, None)
                    if p.paused and server.id in pause_times:
                        try:
                            await p.pause(False)
                        except Exception:
                            log.error(
                                "Exception raised in Audio's emptypause_timer.", exc_info=True
                            )
                    pause_times.pop(server.id, None)
            servers = stop_times.copy()
            servers.update(pause_times)
            for sid in servers:
                server_obj = self.bot.get_guild(sid)
                if sid in stop_times and await self.config.guild(server_obj).emptydc_enabled():
                    emptydc_timer = await self.config.guild(server_obj).emptydc_timer()
                    if (time.time() - stop_times[sid]) >= emptydc_timer:
                        stop_times.pop(sid)
                        try:
                            player = lavalink.get_player(sid)
                            await player.stop()
                            await player.disconnect()
                        except Exception as err:
                            log.error("Exception raised in Audio's emptydc_timer.", exc_info=True)
                            if "No such player for that guild" in str(err):
                                stop_times.pop(sid, None)
                elif (
                    sid in pause_times and await self.config.guild(server_obj).emptypause_enabled()
                ):
                    emptypause_timer = await self.config.guild(server_obj).emptypause_timer()
                    if (time.time() - pause_times.get(sid, 0)) >= emptypause_timer:
                        try:
                            await lavalink.get_player(sid).pause()
                        except Exception as err:
                            if "No such player for that guild" in str(err):
                                pause_times.pop(sid, None)
                            log.error(
                                "Exception raised in Audio's emptypause_timer.", exc_info=True
                            )
            await asyncio.sleep(5)
