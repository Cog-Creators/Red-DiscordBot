from __future__ import annotations

from typing import Dict, Optional

import discord

from redbot.core import Config
from redbot.core.bot import Red


class LocalCacheAgeManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_global: Dict[None, int] = {}

    async def get_global(self) -> int:
        ret: int
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.cache_age()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[int]) -> None:
        if set_to is not None:
            await self._config.global_db_get_timeout.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.global_db_get_timeout.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["cache_age"]

    async def get_context_value(self, guild: discord.Guild = None) -> int:
        return await self.get_global()
