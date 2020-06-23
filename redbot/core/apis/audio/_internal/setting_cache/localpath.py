from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import discord

from redbot.core import Config
from redbot.core.bot import Red


class LocalPathManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
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
