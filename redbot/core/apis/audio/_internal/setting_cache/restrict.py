from __future__ import annotations

from typing import Dict, Optional

import discord

from redbot.core import Config
from redbot.core.bot import Red


class URLRestrictManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_global: Dict[None, bool] = {}

    async def get_global(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.restrict()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[bool]) -> None:
        if set_to is not None:
            await self._config.restrict.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.restrict.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["restrict"]

    async def get_context_value(self, guild: discord.Guild = None) -> bool:
        return await self.get_global()
