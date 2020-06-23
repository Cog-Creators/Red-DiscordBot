from __future__ import annotations

from typing import Dict, Optional

import discord

from redbot.core import Config
from redbot.core.bot import Red

from redbot.core.apis.audio._internal.abstract import CacheLevel


class LocalCacheLevelManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_global: Dict[None, int] = {}

    async def get_global(self) -> CacheLevel:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.cache_level()
            self._cached_global[None] = ret
        return CacheLevel(int(ret))

    async def set_global(self, set_to: Optional[int]) -> None:
        if set_to is not None:
            await self._config.cache_level.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.cache_level.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["cache_level"]

    async def get_context_value(self, guild: discord.Guild = None) -> CacheLevel:
        return await self.get_global()
