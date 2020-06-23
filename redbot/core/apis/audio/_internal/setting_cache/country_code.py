from __future__ import annotations

from typing import Dict, Optional

import discord

from redbot.core import Config
from redbot.core.bot import Red


class CountryCodeManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_user: Dict[int, Optional[str]] = {}
        self._cached_guilds: Dict[int, str] = {}

    async def get_user(self, user: discord.Member) -> Optional[str]:
        ret: Optional[str]
        uid: int = user.id
        if self.enable_cache and uid in self._cached_user:
            ret = self._cached_user[uid]
        else:
            ret = await self._config.user_from_id(uid).country_code()
            self._cached_user[uid] = ret
        return ret

    async def set_user(self, user: discord.Member, set_to: Optional[str]) -> None:
        uid: int = user.id
        if set_to is not None:
            await self._config.user_from_id(uid).country_code.set(set_to)
            self._cached_user[uid] = set_to
        else:
            await self._config.user_from_id(uid).country_code.clear()
            self._cached_user[uid] = self._config.defaults["USER"]["country_code"]

    async def get_guild(self, guild: discord.Guild) -> str:
        ret: str
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guilds:
            ret = self._cached_guilds[gid]
        else:
            ret = await self._config.guild_from_id(gid).country_code()
            self._cached_guilds[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[str]) -> None:
        gid: int = guild.id
        if set_to:
            await self._config.guild_from_id(gid).country_code.set(set_to)
            self._cached_guilds[gid] = set_to
        else:
            await self._config.guild_from_id(gid).ignored.clear()
            self._cached_user[gid] = self._config.defaults["GUILD"]["country_code"]

    async def get_context_value(self, guild: discord.Guild, user: discord.Member,) -> str:
        if (code := await self.get_user(user)) is not None:
            return code
        return await self.get_guild(guild)
