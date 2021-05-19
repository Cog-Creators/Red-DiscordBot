from __future__ import annotations

from typing import Dict, Optional

import discord

from redbot.core import Config
from redbot.core.bot import Red


class EmptyPauseTimerManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_guild: Dict[int, int] = {}

    async def get_guild(self, guild: discord.Guild) -> int:
        ret: int
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid]
        else:
            ret = await self._config.guild_from_id(gid).emptypause_timer()
            self._cached_guild[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[int]) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).emptypause_timer.set(set_to)
            self._cached_guild[gid] = set_to
        else:
            await self._config.guild_from_id(gid).emptypause_timer.clear()
            self._cached_guild[gid] = self._config.defaults["GUILD"]["emptypause_timer"]

    async def get_context_value(self, guild: discord.Guild) -> int:
        return await self.get_guild(guild)
