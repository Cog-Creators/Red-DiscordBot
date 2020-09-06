from __future__ import annotations

from typing import Dict, List, Optional, Union, Set, Iterable, Tuple
import asyncio
from argparse import Namespace
from collections import defaultdict

import discord

from .config import Config
from .utils import AsyncIter


class PrefixManager:
    def __init__(self, config: Config, cli_flags: Namespace):
        self._config: Config = config
        self._global_prefix_overide: Optional[List[str]] = (
            sorted(cli_flags.prefix, reverse=True) or None
        )
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
        # because of discord deletion
        # we now have sync and async access that may need to happen at the
        # same time.
        # blame discord for this.
        self._access_lock = asyncio.Lock()

    async def discord_deleted_user(self, user_id: int):

        async with self._access_lock:

            async for guild_id_or_none, ids in AsyncIter(
                self._cached_whitelist.items(), steps=100
            ):
                ids.discard(user_id)

            async for guild_id_or_none, ids in AsyncIter(
                self._cached_blacklist.items(), steps=100
            ):
                ids.discard(user_id)

            for grp in (self._config.whitelist, self._config.blacklist):
                async with grp() as ul:
                    try:
                        ul.remove(user_id)
                    except ValueError:
                        pass

            # don't use this in extensions, it's optimized and controlled for here,
            # but can't be safe in 3rd party use

            async with self._config._get_base_group("GUILD").all() as abuse:
                for guild_str, guild_data in abuse.items():
                    for l_name in ("whitelist", "blacklist"):
                        try:
                            guild_data[l_name].remove(user_id)
                        except (ValueError, KeyError):
                            pass  # this is raw access not filled with defaults

    async def get_whitelist(self, guild: Optional[discord.Guild] = None) -> Set[int]:
        async with self._access_lock:
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
        async with self._access_lock:
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
                await self._config.guild_from_id(gid).whitelist.set(
                    list(self._cached_whitelist[gid])
                )

    async def clear_whitelist(self, guild: Optional[discord.Guild] = None):
        async with self._access_lock:
            gid: Optional[int] = guild.id if guild else None
            self._cached_whitelist[gid] = set()
            if gid is None:
                await self._config.whitelist.clear()
            else:
                await self._config.guild_from_id(gid).whitelist.clear()

    async def remove_from_whitelist(
        self, guild: Optional[discord.Guild], role_or_user: Iterable[int]
    ):
        async with self._access_lock:
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
                await self._config.guild_from_id(gid).whitelist.set(
                    list(self._cached_whitelist[gid])
                )

    async def get_blacklist(self, guild: Optional[discord.Guild] = None) -> Set[int]:
        async with self._access_lock:
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
        async with self._access_lock:
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
                await self._config.guild_from_id(gid).blacklist.set(
                    list(self._cached_blacklist[gid])
                )

    async def clear_blacklist(self, guild: Optional[discord.Guild] = None):
        async with self._access_lock:
            gid: Optional[int] = guild.id if guild else None
            self._cached_blacklist[gid] = set()
            if gid is None:
                await self._config.blacklist.clear()
            else:
                await self._config.guild_from_id(gid).blacklist.clear()

    async def remove_from_blacklist(
        self, guild: Optional[discord.Guild], role_or_user: Iterable[int]
    ):
        async with self._access_lock:
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
                await self._config.guild_from_id(gid).blacklist.set(
                    list(self._cached_blacklist[gid])
                )


class DisabledCogCache:
    def __init__(self, config: Config):
        self._config = config
        self._disable_map: Dict[str, Dict[int, bool]] = defaultdict(dict)

    async def cog_disabled_in_guild(self, cog_name: str, guild_id: int) -> bool:
        """
        Check if a cog is disabled in a guild

        Parameters
        ----------
        cog_name: str
            This should be the cog's qualified name, not necessarily the classname
        guild_id: int

        Returns
        -------
        bool
        """

        if guild_id in self._disable_map[cog_name]:
            return self._disable_map[cog_name][guild_id]

        gset = await self._config.custom("COG_DISABLE_SETTINGS", cog_name, guild_id).disabled()
        if gset is None:
            gset = await self._config.custom("COG_DISABLE_SETTINGS", cog_name, 0).disabled()
            if gset is None:
                gset = False

        self._disable_map[cog_name][guild_id] = gset
        return gset

    async def default_disable(self, cog_name: str):
        """
        Sets the default for a cog as disabled.

        Parameters
        ----------
        cog_name: str
            This should be the cog's qualified name, not necessarily the classname
        """
        await self._config.custom("COG_DISABLE_SETTINGS", cog_name, 0).disabled.set(True)
        del self._disable_map[cog_name]

    async def default_enable(self, cog_name: str):
        """
        Sets the default for a cog as enabled.

        Parameters
        ----------
        cog_name: str
            This should be the cog's qualified name, not necessarily the classname
        """
        await self._config.custom("COG_DISABLE_SETTINGS", cog_name, 0).disabled.clear()
        del self._disable_map[cog_name]

    async def disable_cog_in_guild(self, cog_name: str, guild_id: int) -> bool:
        """
        Disable a cog in a guild.

        Parameters
        ----------
        cog_name: str
            This should be the cog's qualified name, not necessarily the classname
        guild_id: int

        Returns
        -------
        bool
            Whether or not any change was made.
            This may be useful for settings commands.
        """

        if await self.cog_disabled_in_guild(cog_name, guild_id):
            return False

        self._disable_map[cog_name][guild_id] = True
        await self._config.custom("COG_DISABLE_SETTINGS", cog_name, guild_id).disabled.set(True)
        return True

    async def enable_cog_in_guild(self, cog_name: str, guild_id: int) -> bool:
        """
        Enable a cog in a guild.

        Parameters
        ----------
        cog_name: str
            This should be the cog's qualified name, not necessarily the classname
        guild_id: int

        Returns
        -------
        bool
            Whether or not any change was made.
            This may be useful for settings commands.
        """

        if not await self.cog_disabled_in_guild(cog_name, guild_id):
            return False

        self._disable_map[cog_name][guild_id] = False
        await self._config.custom("COG_DISABLE_SETTINGS", cog_name, guild_id).disabled.set(False)
        return True
