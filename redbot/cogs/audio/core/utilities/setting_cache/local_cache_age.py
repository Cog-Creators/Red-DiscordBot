from __future__ import annotations

from typing import Dict, Optional

import discord

from .abc import CacheBase


class LocalCacheAgeManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
            await self._config.cache_age.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.cache_age.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["cache_age"]

    async def get_context_value(self, guild: discord.Guild = None) -> int:
        return await self.get_global()

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
