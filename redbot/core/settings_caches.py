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
            self._cached.pop(gid, None)
            await self._config.guild_from_id(gid).prefix.set(prefixes)


class IgnoreManager:
    def __init__(self, config: Config):
        self._config: Config = config
        self._cached_channels: Dict[int, bool] = {}
        self._cached_guilds: Dict[int, bool] = {}

    async def get_ignored_channel(
        self, channel: discord.TextChannel, check_category: bool = True
    ) -> bool:
        ret: bool

        cid: int = channel.id
        cat_id: Optional[int] = (
            channel.category.id if check_category and channel.category else None
        )
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


class AllowlistDenylistManager:
    def __init__(self, config: Config):
        self._config: Config = config
        self._cached_allowlist: Dict[Optional[int], List[int]] = {}
        self._cached_denylist: Dict[Optional[int], List[int]] = {}

    async def get_allowlist(self, guild: Optional[discord.Guild] = None) -> List[int]:
        ret: List[int]

        gid: Optional[int] = guild.id if guild else None

        if gid in self._cached_allowlist:
            ret = self._cached_allowlist[gid].copy()
        else:
            if gid is not None:
                ret = await self._config.guild_from_id(gid).allowlist()
                if not ret:
                    ret = []
            else:
                ret = await self._config.allowlist()

            self._cached_allowlist[gid] = ret.copy()

        return ret

    async def add_to_allowlist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Allowlisted objects must be a list of ints")

        if gid is None:
            if gid not in self._cached_allowlist:
                self._cached_allowlist[gid] = await self._config.allowlist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_allowlist[gid]:
                    self._cached_allowlist[gid].append(obj_id)
                    async with self._config.allowlist() as curr_list:
                        curr_list.append(obj_id)
        else:
            if gid not in self._cached_allowlist:
                self._cached_allowlist[gid] = await self._config.guild_from_id(gid).allowlist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_allowlist[gid]:
                    self._cached_allowlist[gid].append(obj_id)
                    async with self._config.guild_from_id(gid).allowlist() as curr_list:
                        curr_list.append(obj_id)

    async def clear_allowlist(self, guild: Optional[discord.Guild] = None):
        gid: Optional[int] = guild.id if guild else None
        self._cached_allowlist[gid] = []
        if gid is None:
            await self._config.allowlist.clear()
        else:
            await self._config.guild_from_id(gid).allowlist.clear()

    async def remove_from_allowlist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Allowlisted objects must be a list of ints")

        if gid is None:
            if gid not in self._cached_allowlist:
                self._cached_allowlist[gid] = await self._config.allowlist()
            for obj_id in role_or_user:
                if obj_id in self._cached_allowlist[gid]:
                    self._cached_allowlist[gid].remove(obj_id)
                    async with self._config.allowlist() as curr_list:
                        curr_list.remove(obj_id)
        else:
            if gid not in self._cached_allowlist:
                self._cached_allowlist[gid] = await self._config.guild_from_id(gid).allowlist()
            for obj_id in role_or_user:
                if obj_id in self._cached_allowlist[gid]:
                    self._cached_allowlist[gid].remove(obj_id)
                    async with self._config.guild_from_id(gid).allowlist() as curr_list:
                        curr_list.remove(obj_id)

    async def get_denylist(self, guild: Optional[discord.Guild] = None) -> List[int]:
        ret: List[int]

        gid: Optional[int] = guild.id if guild else None

        if gid in self._cached_denylist:
            ret = self._cached_denylist[gid].copy()
        else:
            if gid is not None:
                ret = await self._config.guild_from_id(gid).denylist()
                if not ret:
                    ret = []
            else:
                ret = await self._config.denylist()

            self._cached_denylist[gid] = ret.copy()

        return ret

    async def add_to_denylist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Denylisted objects must be a list of ints")
        if gid is None:
            if gid not in self._cached_denylist:
                self._cached_denylist[gid] = await self._config.denylist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_denylist[gid]:
                    self._cached_denylist[gid].append(obj_id)
                    async with self._config.denylist() as curr_list:
                        curr_list.append(obj_id)
        else:
            if gid not in self._cached_denylist:
                self._cached_denylist[gid] = await self._config.guild_from_id(gid).denylist()
            for obj_id in role_or_user:
                if obj_id not in self._cached_denylist[gid]:
                    self._cached_denylist[gid].append(obj_id)
                    async with self._config.guild_from_id(gid).denylist() as curr_list:
                        curr_list.append(obj_id)

    async def clear_denylist(self, guild: Optional[discord.Guild] = None):
        gid: Optional[int] = guild.id if guild else None
        self._cached_denylist[gid] = []
        if gid is None:
            await self._config.denylist.clear()
        else:
            await self._config.guild_from_id(gid).denylist.clear()

    async def remove_from_denylist(self, guild: Optional[discord.Guild], role_or_user: List[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not isinstance(role_or_user, list) or not all(
            isinstance(r_or_u, int) for r_or_u in role_or_user
        ):
            raise TypeError("Denylisted objects must be a list of ints")
        if gid is None:
            if gid not in self._cached_denylist:
                self._cached_denylist[gid] = await self._config.denylist()
            for obj_id in role_or_user:
                if obj_id in self._cached_denylist[gid]:
                    self._cached_denylist[gid].remove(obj_id)
                    async with self._config.denylist() as curr_list:
                        curr_list.remove(obj_id)
        else:
            if gid not in self._cached_denylist:
                self._cached_denylist[gid] = await self._config.guild_from_id(gid).denylist()
            for obj_id in role_or_user:
                if obj_id in self._cached_denylist[gid]:
                    self._cached_denylist[gid].remove(obj_id)
                    async with self._config.guild_from_id(gid).denylist() as curr_list:
                        curr_list.remove(obj_id)
