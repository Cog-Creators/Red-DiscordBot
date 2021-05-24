from __future__ import annotations

from typing import Dict, Optional

import discord

from .abc import CacheBase


class MaxTrackLengthManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_guild",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_guild: Dict[int, int] = {}
        self._cached_global: Dict[None, int] = {}

    async def get_guild(self, guild: discord.Guild) -> int:
        ret: int
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid]
        else:
            ret = await self._config.guild_from_id(gid).maxlength()
            self._cached_guild[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[int]) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).maxlength.set(set_to)
            self._cached_guild[gid] = set_to
        else:
            await self._config.guild_from_id(gid).maxlength.clear()
            self._cached_guild[gid] = self._config.defaults["GUILD"]["maxlength"]

    async def get_global(self) -> int:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.maxlength()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[int]) -> None:
        if set_to is not None:
            await self._config.maxlength.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.maxlength.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["maxlength"]

    async def get_context_value(self, guild: discord.Guild) -> int:
        guild_time = await self.get_guild(guild)
        global_time = await self.get_global()
        if global_time == 0 or global_time > guild_time:
            return guild_time
        return global_time

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
