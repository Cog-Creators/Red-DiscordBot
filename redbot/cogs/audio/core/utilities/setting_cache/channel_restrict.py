from __future__ import annotations

from typing import Dict, Optional, Set, Union

import discord

from redbot.core import Config
from redbot.core.bot import Red


class ChannelRestrictManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_vc: Dict[Optional[int], Set[int]] = {}
        self._cached_text: Dict[Optional[int], Set[int]] = {}

    async def get_context_vc(self, guild: discord.Guild) -> Set[discord.VoiceChannel]:
        ret: Set[int]
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_vc:
            ret = self._cached_vc[gid].copy()
        else:
            ret = await self._config.guild_from_id(gid).whitelisted_vc()
            self._cached_vc[gid] = set(ret.copy())

        return {vc for cid in ret if (vc := self.bot.get_channel(cid)) is not None}

    async def add_to_vc_whitelist(self, guild: discord.Guild, ids: Set[int]) -> None:
        gid: int = guild.id
        ids = ids or set()
        if not isinstance(ids, set) or any(not isinstance(s, int) for s in ids):
            raise TypeError("IDs objects must be a set of ints")
        if gid not in self._cached_vc:
            self._cached_vc[gid] = set(await self._config.guild_from_id(gid).whitelisted_vc())
        for cid in ids:
            if cid not in self._cached_vc[gid]:
                self._cached_vc[gid].add(cid)
                async with self._config.guild_from_id(gid).whitelisted_vc() as curr_list:
                    if cid not in curr_list:
                        curr_list.append(cid)

    async def clear_vc_whitelist(self, guild: discord.Guild) -> None:
        gid: int = guild.id
        self._cached_vc[gid] = set()
        await self._config.guild_from_id(gid).whitelisted_vc.clear()

    async def remove_from_vc_whitelist(self, guild: discord.Guild, ids: Set[int]) -> None:
        gid: int = guild.id
        ids = ids or set()
        if not isinstance(ids, set) or any(not isinstance(s, int) for s in ids):
            raise TypeError("IDs objects must be a set of ints")
        if gid not in self._cached_vc:
            self._cached_vc[gid] = set(await self._config.guild_from_id(gid).whitelisted_vc())
        for cid in ids:
            if cid in self._cached_vc[gid]:
                self._cached_vc[gid].remove(cid)
                async with self._config.guild_from_id(gid).whitelisted_vc() as curr_list:
                    if cid in curr_list:
                        curr_list.remove(cid)

    async def get_context_text(self, guild: discord.Guild) -> Set[discord.TextChannel]:
        ret: Set[int]
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_text:
            ret = self._cached_text[gid].copy()
        else:
            ret = await self._config.guild_from_id(gid).whitelisted_text()
            self._cached_text[gid] = set(ret.copy())

        return {text for cid in ret if (text := self.bot.get_channel(cid)) is not None}

    async def add_to_text_whitelist(self, guild: discord.Guild, ids: Set[int]) -> None:
        gid: int = guild.id
        ids = ids or set()
        if not isinstance(ids, set) or any(not isinstance(s, int) for s in ids):
            raise TypeError("IDs objects must be a set of ints")
        if gid not in self._cached_text:
            self._cached_text[gid] = set(await self._config.guild_from_id(gid).whitelisted_text())
        for cid in ids:
            if cid not in self._cached_text[gid]:
                self._cached_text[gid].add(cid)
                async with self._config.guild_from_id(gid).whitelisted_text() as curr_list:
                    if cid not in curr_list:
                        curr_list.append(cid)

    async def clear_text_whitelist(self, guild: discord.Guild) -> None:
        gid: int = guild.id
        self._cached_text[gid] = set()
        await self._config.guild_from_id(gid).whitelisted_text.clear()

    async def remove_from_text_whitelist(self, guild: discord.Guild, ids: Set[int]) -> None:
        gid: int = guild.id
        ids = ids or set()
        if not isinstance(ids, set) or any(not isinstance(s, int) for s in ids):
            raise TypeError("IDs objects must be a set of ints")
        if gid not in self._cached_text:
            self._cached_text[gid] = set(await self._config.guild_from_id(gid).whitelisted_text())
        for cid in ids:
            if cid in self._cached_text[gid]:
                self._cached_text[gid].remove(cid)
                async with self._config.guild_from_id(gid).whitelisted_text() as curr_list:
                    if cid in curr_list:
                        curr_list.remove(cid)

    async def allowed_by_whitelist(
        self,
        what: Union[discord.TextChannel, discord.VoiceChannel],
        guild: Union[discord.Guild, int],
    ) -> bool:
        if isinstance(guild, int):
            guild = await self.bot.get_guild(guild)
        if isinstance(what, discord.VoiceChannel):
            if allowed := await self.get_context_vc(guild):
                return what in allowed
        elif isinstance(what, discord.TextChannel):
            if allowed := await self.get_context_text(guild):
                return what in allowed
        return True
