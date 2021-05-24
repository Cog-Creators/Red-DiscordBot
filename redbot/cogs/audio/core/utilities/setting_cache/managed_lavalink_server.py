from __future__ import annotations

from typing import Dict, Optional

import discord

from .abc import CacheBase


class ManagedLavalinkManager(CacheBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_global: Dict[None, bool] = {}

    async def get_global(self) -> bool:
        ret: bool
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.use_external_lavalink()
            self._cached_global[None] = ret
        return ret

    async def set_global(self, set_to: Optional[bool]) -> None:
        if set_to is not None:
            await self._config.use_external_lavalink.set(set_to)
            self._cached_global[None] = set_to
        else:
            await self._config.use_external_lavalink.clear()
            self._cached_global[None] = self._config.defaults["GLOBAL"]["use_external_lavalink"]

    async def get_context_value(self, guild: discord.Guild = None) -> bool:
        return await self.get_global()

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
