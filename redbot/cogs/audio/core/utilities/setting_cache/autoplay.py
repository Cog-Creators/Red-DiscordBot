from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING, Tuple

import discord

from .abc import CachingABC
from redbot.core import Config
from redbot.core.bot import Red

if TYPE_CHECKING:
    from . import AutoDCManager


class AutoPlayManager(CachingABC):
    def __init__(
        self, bot: Red, config: Config, enable_cache: bool = True, disconnect: AutoDCManager = None
    ):
        self._config: Config = config
        self.bot = bot
        self._disconnect = disconnect
        self.enable_cache = enable_cache
        self._cached: Dict[int, bool] = {}
        self._currently_in_cache: Dict[int, Tuple[int, int]] = {}

    async def get_guild(self, guild: discord.Guild) -> bool:
        ret: bool
        gid: int = guild.id
        if self.enable_cache and gid in self._cached:
            ret = self._cached[gid]
        else:
            ret = await self._config.guild_from_id(gid).auto_play()
            self._cached[gid] = ret
        return ret

    async def get_currently_in_guild(self, guild: discord.Guild) -> Tuple[int, int]:
        ret: Tuple[int, int]
        gid: int = guild.id
        if self.enable_cache and gid in self._currently_in_cache:
            ret = self._currently_in_cache[gid]
        else:
            ret = await self._config.guild_from_id(gid).currently_auto_playing_in()
            self._currently_in_cache[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[bool]) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).auto_play.set(set_to)
            self._cached[gid] = set_to
        else:
            await self._config.guild_from_id(gid).auto_play.clear()
            self._cached[gid] = self._config.defaults["GUILD"]["auto_play"]

    async def set_currently_in_guild(
        self, guild: discord.Guild, set_to: Optional[Tuple[int, int]] = None
    ) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).currently_auto_playing_in.set(set_to)
            self._currently_in_cache[gid] = set_to
        else:
            await self._config.guild_from_id(gid).currently_auto_playing_in.clear()
            self._currently_in_cache[gid] = self._config.defaults["GUILD"][
                "currently_auto_playing_in"
            ]

    async def get_context_value(self, guild: discord.Guild) -> bool:
        if (
            await self._disconnect.get_global() is True
            or await self._disconnect.get_guild(guild) is True
        ):
            return False
        return await self.get_guild(guild)

    async def get_currently_in_context_value(self, guild: discord.Guild) -> Tuple[int, int]:
        return await self.get_currently_in_guild(guild)

    def reset_globals(self) -> None:
        pass
