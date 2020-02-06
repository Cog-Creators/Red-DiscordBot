from __future__ import annotations

from typing import Dict, List, Optional, Union
from argparse import Namespace

import discord

from .config import Config


class PrefixManager:
    def __init__(self, config: Config, cli_flags: Namespace):
        self._config: Config = config
        self._global_prefix_overide: Optional[List[str]] = sorted(
            cli_flags.prefix, reverse=True
        ) or None
        self._cached: Dict[Optional[int], List[str]] = {}

    async def get_prefixes(self, guild: Optional[discord.Guild] = None) -> List[str]:
        ret: List[str]

        gid: Optional[int] = guild.id if guild else None

        if gid in self._cached:
            ret = self._cached[gid].copy()
        else:
            if gid is not None:
                ret = await self._config.guild_from_id(gid).prefix()
                if not ret:
                    ret = await self.get_prefixes(None)
            else:
                ret = self._global_prefix_overide or (await self._config.prefix())

            self._cached[gid] = ret.copy()

        return ret

    async def set_prefixes(
        self, guild: Optional[discord.Guild] = None, prefixes: Optional[List[str]] = None
    ):
        gid: Optional[int] = guild.id if guild else None
        prefixes = prefixes or []
        if not isinstance(prefixes, list) and not all(isinstance(pfx, str) for pfx in prefixes):
            raise TypeError("Prefixes must be a list of strings")
        prefixes = sorted(prefixes, reverse=True)
        if gid is None:
            if not prefixes:
                raise ValueError("You must have at least one prefix.")
            self._cached.clear()
            await self._config.prefix.set(prefixes)
        else:
            del self._cached[gid]
            await self._config.guild_from_id(gid).prefix.set(prefixes)


class IgnoreManager:
    def __init__(self, config: Config):
        self._config: Config = config
        self._cached_channels: Dict[int, bool] = {}
        self._cached_guilds: Dict[int, bool] = {}

    async def get_ignored_channel(self, channel: discord.TextChannel) -> bool:
        ret: bool

        cid: int = channel.id
        cat_id: Optional[int] = channel.category.id if channel.category else None
        if cid in self._cached_channels:
            chan_ret = self._cached_channels[cid]
        else:
            chan_ret = await self._config.channel_from_id(cid).ignored()
            self._cached_channels[cid] = chan_ret
        if cat_id and cat_id in self._cached_channels:
            cat_ret = self._cached_channels[cat_id]
        else:
            if cat_id:
                cat_ret = await self._config.channel_from_id(cat_id).ignored()
                self._cached_channels[cat_id] = cat_ret
            else:
                cat_ret = False
        ret = chan_ret or cat_ret

        return ret

    async def set_ignored_channel(
        self, channel: Union[discord.TextChannel, discord.CategoryChannel], set_to: bool
    ):

        cid: int = channel.id
        self._cached_channels[cid] = set_to
        if set_to:
            await self._config.channel_from_id(cid).ignored.set(set_to)
        else:
            await self._config.channel_from_id(cid).ignored.clear()

    async def get_ignored_guild(self, guild: discord.Guild) -> bool:
        ret: bool

        gid: int = guild.id

        if gid in self._cached_guilds:
            ret = self._cached_guilds[gid]
        else:
            ret = await self._config.guild_from_id(gid).ignored()
            self._cached_guilds[gid] = ret

        return ret

    async def set_ignored_guild(self, guild: discord.Guild, set_to: bool):

        gid: int = guild.id
        self._cached_guilds[gid] = set_to
        if set_to:
            await self._config.guild_from_id(gid).ignored.set(set_to)
        else:
            await self._config.guild_from_id(gid).ignored.clear()


class WhitelistBlacklistManager:
    def __init__(self, config: Config):
        self._config: Config = config
        self._cached_whitelist: Dict[Optional[int], List[int]] = {}
        self._cached_blacklist: Dict[Optional[int], List[int]] = {}

    async def get_whitelist(self, guild: Optional[discord.Guild] = None) -> List[int]:
        ret: List[int]

        gid: Optional[int] = guild.id if guild else None

        if gid in self._cached_whitelist:
            ret = self._cached_whitelist[gid].copy()
        else:
            if gid is not None:
                ret = await self._config.guild_from_id(gid).whitelist()
                if not ret:
                    ret = []
            else:
                ret = await self._config.whitelist()

            self._cached_whitelist[gid] = ret.copy()

        return ret

    async def add_to_whitelist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Whitelisted objects must be a list of ints")

        if gid is None:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = await self._config.whitelist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].append(obj_id)
                    async with self._config.whitelist() as curr_list:
                        curr_list.append(obj_id)
        else:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = await self._config.guild_from_id(gid).whitelist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].append(obj_id)
                    async with self._config.guild_from_id(gid).whitelist() as curr_list:
                        curr_list.append(obj_id)

    async def clear_whitelist(self, guild: Optional[discord.Guild] = None):
        gid: Optional[int] = guild.id if guild else None
        self._cached_whitelist[gid] = []
        if gid is None:
            await self._config.whitelist.clear()
        else:
            await self._config.guild_from_id(gid).whitelist.clear()

    async def remove_from_whitelist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Whitelisted objects must be a list of ints")

        if gid is None:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = await self._config.whitelist()
            for obj_id in role_or_user:
                if obj_id in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].remove(obj_id)
                    async with self._config.whitelist() as curr_list:
                        curr_list.remove(obj_id)
        else:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = await self._config.guild_from_id(gid).whitelist()
            for obj_id in role_or_user:
                if obj_id in self._cached_whitelist[gid]:
                    self._cached_whitelist[gid].remove(obj_id)
                    async with self._config.guild_from_id(gid).whitelist() as curr_list:
                        curr_list.remove(obj_id)

    async def get_blacklist(self, guild: Optional[discord.Guild] = None) -> List[int]:
        ret: List[int]

        gid: Optional[int] = guild.id if guild else None

        if gid in self._cached_blacklist:
            ret = self._cached_blacklist[gid].copy()
        else:
            if gid is not None:
                ret = await self._config.guild_from_id(gid).blacklist()
                if not ret:
                    ret = []
            else:
                ret = await self._config.blacklist()

            self._cached_blacklist[gid] = ret.copy()

        return ret

    async def add_to_blacklist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Blacklisted objects must be a list of ints")
        if gid is None:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = await self._config.blacklist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].append(obj_id)
                    async with self._config.blacklist() as curr_list:
                        curr_list.append(obj_id)
        else:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = self._config.guild_from_id(gid).blacklist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].append(obj_id)
                    async with self._config.guild_from_id(gid).blacklist() as curr_list:
                        curr_list.append(obj_id)

    async def clear_blacklist(self, guild: Optional[discord.Guild] = None):
        gid: Optional[int] = guild.id if guild else None
        self._cached_blacklist[gid] = []
        if gid is None:
            await self._config.blacklist.clear()
        else:
            await self._config.guild_from_id(gid).blacklist.clear()

    async def remove_from_blacklist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Blacklisted objects must be a list of ints")
        if gid is None:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = await self._config.blacklist()
            for obj_id in role_or_user:
                if obj_id in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].remove(obj_id)
                    async with self._config.blacklist() as curr_list:
                        curr_list.remove(obj_id)
        else:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = self._config.guild_from_id(gid).blacklist()
            for obj_id in role_or_user:
                if obj_id in self._cached_blacklist[gid]:
                    self._cached_blacklist[gid].remove(obj_id)
                    async with self._config.guild_from_id(gid).blacklist() as curr_list:
                        curr_list.remove(obj_id)
