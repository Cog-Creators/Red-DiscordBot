from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import discord

from .abc import CacheBase


class LocalPathManager(CacheBase):
    __slots__ = (
        "_config",
        "bot",
        "enable_cache",
        "config_cache",
        "_cached_global",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_global: Dict[None, str] = {}

    async def get_global(self) -> Path:
        ret: str
        if self.enable_cache and None in self._cached_global:
            ret = self._cached_global[None]
        else:
            ret = await self._config.localpath()
            self._cached_global[None] = ret
        return Path(ret).absolute()

    async def set_global(self, set_to: Optional[Path]) -> None:
        gid = None
        if set_to is not None:
            await self._config.localpath.set(set_to)
            self._cached_global[gid] = str(set_to.absolute())
        else:
            await self._config.localpath.clear()
            self._cached_global[gid] = self._config.defaults["GLOBAL"]["localpath"]

    async def get_context_value(self, guild: discord.Guild = None) -> Path:
        return await self.get_global()

    def reset_globals(self) -> None:
        if None in self._cached_global:
            del self._cached_global[None]
