from __future__ import annotations

from typing import Dict, Optional, Set, Union

import discord

from redbot.core import Config
from redbot.core.bot import Red


class WhitelistBlacklistManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self._cached_whitelist: Dict[Optional[int], Set[str]] = {}
        self._cached_blacklist: Dict[Optional[int], Set[str]] = {}

    async def get_whitelist(self, guild: Optional[discord.Guild] = None) -> Set[str]:
        ret: Set[str]
        gid: Optional[int] = guild.id if guild else None
        if self.enable_cache and gid in self._cached_whitelist:
            ret = self._cached_whitelist[gid].copy()
        else:
            if gid is not None:
                ret = set(await self._config.guild_from_id(gid).url_keyword_whitelist())
                if not ret:
                    ret = set()
            else:
                ret = set(await self._config.url_keyword_whitelist())

            self._cached_whitelist[gid] = ret.copy()

        return {i.lower() for i in ret}

    async def add_to_whitelist(self, guild: Optional[discord.Guild], strings: Set[str]) -> None:
        gid: Optional[int] = guild.id if guild else None
        strings = strings or set()
        if not isinstance(strings, set) or any(not isinstance(s, str) for s in strings):
            raise TypeError("Whitelisted objects must be a set of strings")
        if gid is None:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(await self._config.url_keyword_whitelist())
            for string in strings:
                if string not in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].add(string)
                    async with self._config.url_keyword_whitelist() as curr_list:
                        curr_list.append(string)
        else:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(
                    await self._config.guild_from_id(gid).url_keyword_whitelist()
                )
            for string in strings:
                if string not in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].add(string)
                    async with self._config.guild_from_id(
                        gid
                    ).url_keyword_whitelist() as curr_list:
                        curr_list.append(string)

    async def clear_whitelist(self, guild: Optional[discord.Guild] = None) -> None:
        gid: Optional[int] = guild.id if guild else None
        self._cached_whitelist[gid] = set()
        if gid is None:
            await self._config.url_keyword_whitelist.clear()
        else:
            await self._config.guild_from_id(gid).url_keyword_whitelist.clear()

    async def remove_from_whitelist(
        self, guild: Optional[discord.Guild], strings: Set[str]
    ) -> None:
        gid: Optional[int] = guild.id if guild else None
        strings = strings or set()
        if not isinstance(strings, set) or any(not isinstance(s, str) for s in strings):
            raise TypeError("Whitelisted objects must be a set of strings")
        if gid is None:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(await self._config.url_keyword_whitelist())
            for string in strings:
                if string in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].remove(string)
                    async with self._config.url_keyword_whitelist() as curr_list:
                        curr_list.remove(string)
        else:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(
                    await self._config.guild_from_id(gid).url_keyword_whitelist()
                )
            for string in strings:
                if string in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].remove(string)
                    async with self._config.guild_from_id(
                        gid
                    ).url_keyword_whitelist() as curr_list:
                        curr_list.remove(string)

    async def get_blacklist(self, guild: Optional[discord.Guild] = None) -> Set[str]:
        ret: Set[str]
        gid: Optional[int] = guild.id if guild else None
        if self.enable_cache and gid in self._cached_blacklist:
            ret = self._cached_blacklist[gid].copy()
        else:
            if gid is not None:
                ret = set(await self._config.guild_from_id(gid).url_keyword_blacklist())
                if not ret:
                    ret = set()
            else:
                ret = set(await self._config.url_keyword_blacklist())
            self._cached_blacklist[gid] = ret.copy()
        return {i.lower() for i in ret}

    async def add_to_blacklist(self, guild: Optional[discord.Guild], strings: Set[str]) -> None:
        gid: Optional[int] = guild.id if guild else None
        strings = strings or set()
        if not isinstance(strings, set) or any(not isinstance(r_or_u, str) for r_or_u in strings):
            raise TypeError("Blacklisted objects must be a set of strings")
        if gid is None:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(await self._config.url_keyword_blacklist())
            for string in strings:
                if string not in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].add(string)
                    async with self._config.url_keyword_blacklist() as curr_list:
                        curr_list.append(string)
        else:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(
                    await self._config.guild_from_id(gid).url_keyword_blacklist()
                )
            for string in strings:
                if string not in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].add(string)
                    async with self._config.guild_from_id(
                        gid
                    ).url_keyword_blacklist() as curr_list:
                        curr_list.append(string)

    async def clear_blacklist(self, guild: Optional[discord.Guild] = None) -> None:
        gid: Optional[int] = guild.id if guild else None
        self._cached_blacklist[gid] = set()
        if gid is None:
            await self._config.url_keyword_blacklist.clear()
        else:
            await self._config.guild_from_id(gid).url_keyword_blacklist.clear()

    async def remove_from_blacklist(
        self, guild: Optional[discord.Guild], strings: Set[str]
    ) -> None:
        gid: Optional[int] = guild.id if guild else None
        strings = strings or set()
        if not isinstance(strings, set) or any(not isinstance(r_or_u, str) for r_or_u in strings):
            raise TypeError("Blacklisted objects must be a set of strings")
        if gid is None:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(await self._config.url_keyword_blacklist())
            for string in strings:
                if string in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].remove(string)
                    async with self._config.url_keyword_blacklist() as curr_list:
                        curr_list.remove(string)
        else:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(
                    await self._config.guild_from_id(gid).url_keyword_blacklist()
                )
            for string in strings:
                if string in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].remove(string)
                    async with self._config.guild_from_id(
                        gid
                    ).url_keyword_blacklist() as curr_list:
                        curr_list.remove(string)

    async def allowed_by_whitelist_blacklist(
        self, what: Optional[str] = None, *, guild: Optional[Union[discord.Guild, int]] = None,
    ) -> bool:
        if isinstance(guild, int):
            guild = self.bot.get_guild(guild)
        if global_whitelist := await self.get_whitelist():
            if what not in global_whitelist:
                return False
        else:
            # blacklist is only used when whitelist doesn't exist.
            global_blacklist = await self.get_blacklist()
            if what in global_blacklist:
                return False
        if guild:
            if guild_whitelist := await self.get_whitelist(guild):
                if what in guild_whitelist:
                    return False
            else:
                guild_blacklist = await self.get_blacklist(guild)
                if what in guild_blacklist:
                    return False
        return True

    async def get_context_whitelist(
        self, guild: Optional[discord.Guild] = None, printable: bool = False
    ) -> Set[str]:
        global_whitelist = await self.get_whitelist()
        if printable:
            global_whitelist = {f"{s} * Global" for s in global_whitelist}
        if guild:
            context_whitelist = await self.get_whitelist(guild)
        else:
            context_whitelist = set()
        context_whitelist.update(global_whitelist)
        return context_whitelist

    async def get_context_blacklist(
        self, guild: Optional[discord.Guild] = None, printable: bool = False
    ) -> Set[str]:
        global_blacklist = await self.get_blacklist()
        if printable:
            global_blacklist = {f"{s} * Global" for s in global_blacklist}
        if guild:
            context_whitelist = await self.get_blacklist(guild)
        else:
            context_whitelist = set()
        context_whitelist.update(global_blacklist)
        return context_whitelist
