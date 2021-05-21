from __future__ import annotations

from typing import Dict, Optional

import discord

from .abc import CachingABC
from redbot.core import Config
from redbot.core.bot import Red


class JukeboxPriceManager(CachingABC):
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_guild: Dict[int, int] = {}
        self._cached_global: Dict[None, int] = {}

    async def get_guild(self, guild: discord.Guild) -> int:
        ret: int
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid]
        else:
            ret = await self._config.guild_from_id(gid).jukebox_price()
            self._cached_guild[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[int]) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).jukebox_price.set(set_to)
            self._cached_guild[gid] = set_to
        else:
            await self._config.guild_from_id(gid).jukebox_price.clear()
            self._cached_guild[gid] = self._config.defaults["GUILD"]["jukebox_price"]

    async def get_global(self) -> int:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.jukebox_price()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[int]) -> None:
        if set_to is not None:
            await self._config.jukebox_price.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.empty.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["jukebox_price"]

    async def get_context_value(self, guild: discord.Guild) -> int:
        guild_value = await self.get_guild(guild)
        global_value = await self.get_global()
        if global_value == 0 or guild_value > global_value:
            return guild_value
        return global_value

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
