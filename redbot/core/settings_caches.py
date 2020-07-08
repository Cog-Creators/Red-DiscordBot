from __future__ import annotations

from typing import Dict, List, Optional, Union, Set, Iterable
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


class WhitelistBlacklistManager:
    def __init__(self, config: Config):
        self._config: Config = config
        self._cached_whitelist: Dict[Optional[int], Set[int]] = {}
        self._cached_blacklist: Dict[Optional[int], Set[int]] = {}

    async def get_whitelist(self, guild: Optional[discord.Guild] = None) -> Set[int]:
        ret: Set[int]

        gid: Optional[int] = guild.id if guild else None

        if gid in self._cached_whitelist:
            ret = self._cached_whitelist[gid].copy()
        else:
            if gid is not None:
                ret = set(await self._config.guild_from_id(gid).whitelist())
            else:
                ret = set(await self._config.whitelist())

            self._cached_whitelist[gid] = ret.copy()

        return ret

    async def add_to_whitelist(self, guild: Optional[discord.Guild], role_or_user: Iterable[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not all(isinstance(r_or_u, int) for r_or_u in role_or_user):
            raise TypeError("`role_or_user` must be an iterable of `int`s.")

        if gid is None:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(await self._config.whitelist())
            self._cached_whitelist[gid].update(role_or_user)
            await self._config.whitelist.set(list(self._cached_whitelist[gid]))

        else:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(
                    await self._config.guild_from_id(gid).whitelist()
                )
            self._cached_whitelist[gid].update(role_or_user)
            await self._config.guild_from_id(gid).whitelist.set(list(self._cached_whitelist[gid]))

    async def clear_whitelist(self, guild: Optional[discord.Guild] = None):
        gid: Optional[int] = guild.id if guild else None
        self._cached_whitelist[gid] = set()
        if gid is None:
            await self._config.whitelist.clear()
        else:
            await self._config.guild_from_id(gid).whitelist.clear()

    async def remove_from_whitelist(
        self, guild: Optional[discord.Guild], role_or_user: Iterable[int]
    ):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not all(isinstance(r_or_u, int) for r_or_u in role_or_user):
            raise TypeError("`role_or_user` must be an iterable of `int`s.")

        if gid is None:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(await self._config.whitelist())
            self._cached_whitelist[gid].difference_update(role_or_user)
            await self._config.whitelist.set(list(self._cached_whitelist[gid]))

        else:
            if gid not in self._cached_whitelist:
                self._cached_whitelist[gid] = set(
                    await self._config.guild_from_id(gid).whitelist()
                )
            self._cached_whitelist[gid].difference_update(role_or_user)
            await self._config.guild_from_id(gid).whitelist.set(list(self._cached_whitelist[gid]))

    async def get_blacklist(self, guild: Optional[discord.Guild] = None) -> Set[int]:
        ret: Set[int]

        gid: Optional[int] = guild.id if guild else None

        if gid in self._cached_blacklist:
            ret = self._cached_blacklist[gid].copy()
        else:
            if gid is not None:
                ret = set(await self._config.guild_from_id(gid).blacklist())
            else:
                ret = set(await self._config.blacklist())

            self._cached_blacklist[gid] = ret.copy()

        return ret

    async def add_to_blacklist(self, guild: Optional[discord.Guild], role_or_user: Iterable[int]):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not all(isinstance(r_or_u, int) for r_or_u in role_or_user):
            raise TypeError("`role_or_user` must be an iterable of `int`s.")
        if gid is None:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(await self._config.blacklist())
            self._cached_blacklist[gid].update(role_or_user)
            await self._config.blacklist.set(list(self._cached_blacklist[gid]))
        else:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(
                    await self._config.guild_from_id(gid).blacklist()
                )
            self._cached_blacklist[gid].update(role_or_user)
            await self._config.guild_from_id(gid).blacklist.set(list(self._cached_blacklist[gid]))

    async def clear_blacklist(self, guild: Optional[discord.Guild] = None):
        gid: Optional[int] = guild.id if guild else None
        self._cached_blacklist[gid] = set()
        if gid is None:
            await self._config.blacklist.clear()
        else:
            await self._config.guild_from_id(gid).blacklist.clear()

    async def remove_from_blacklist(
        self, guild: Optional[discord.Guild], role_or_user: Iterable[int]
    ):
        gid: Optional[int] = guild.id if guild else None
        role_or_user = role_or_user or []
        if not all(isinstance(r_or_u, int) for r_or_u in role_or_user):
            raise TypeError("`role_or_user` must be an iterable of `int`s.")
        if gid is None:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(await self._config.blacklist())
            self._cached_blacklist[gid].difference_update(role_or_user)
            await self._config.blacklist.set(list(self._cached_blacklist[gid]))
        else:
            if gid not in self._cached_blacklist:
                self._cached_blacklist[gid] = set(
                    await self._config.guild_from_id(gid).blacklist()
                )
            self._cached_blacklist[gid].difference_update(role_or_user)
            await self._config.guild_from_id(gid).blacklist.set(list(self._cached_blacklist[gid]))
