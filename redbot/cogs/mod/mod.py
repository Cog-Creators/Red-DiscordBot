import asyncio
import logging
import re
from abc import ABC
from collections import defaultdict
from typing import List, Tuple

import discord
from redbot.core import Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils._internal_utils import send_to_owners_with_prefix_replaced
from .casetypes import CASETYPES
from .events import Events
from .kickban import KickBanMixin
from .mutes import MuteMixin
from .names import ModInfo
from .slowmode import Slowmode
from .settings import ModSettings

_ = T_ = Translator("Mod", __file__)

__version__ = "1.2.0"


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


@cog_i18n(_)
class Mod(
    ModSettings,
    Events,
    KickBanMixin,
    MuteMixin,
    ModInfo,
    Slowmode,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """Moderation tools."""

    default_global_settings = {"version": ""}

    default_guild_settings = {
        "ban_mention_spam": False,
        "delete_repeats": -1,
        "ignored": False,
        "respect_hierarchy": True,
        "delete_delay": -1,
        "reinvite_on_unban": False,
        "current_tempbans": [],
        "dm_on_kickban": False,
        "default_days": 0,
    }

    default_channel_settings = {"ignored": False}

    default_member_settings = {"past_nicks": [], "perms_cache": {}, "banned_until": False}

    default_user_settings = {"past_names": []}

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

        self.config = Config.get_conf(self, 4961522000, force_registration=True)
        self.config.register_global(**self.default_global_settings)
        self.config.register_guild(**self.default_guild_settings)
        self.config.register_channel(**self.default_channel_settings)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.cache: dict = {}
        self.tban_expiry_task = self.bot.loop.create_task(self.check_tempban_expirations())
        self.last_case: dict = defaultdict(dict)

        self._ready = asyncio.Event()

    async def initialize(self):
        await self._maybe_update_config()
        self._ready.set()

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        await self._ready.wait()

    def cog_unload(self):
        self.tban_expiry_task.cancel()

    async def _maybe_update_config(self):
        """Maybe update `delete_delay` value set by Config prior to Mod 1.0.0."""
        if not await self.config.version():
            guild_dict = await self.config.all_guilds()
            for guild_id, info in guild_dict.items():
                delete_repeats = info.get("delete_repeats", False)
                if delete_repeats:
                    val = 3
                else:
                    val = -1
                await self.config.guild(discord.Object(id=guild_id)).delete_repeats.set(val)
            await self.config.version.set("1.0.0")  # set version of last update
        if await self.config.version() < "1.1.0":
            msg = _(
                "Ignored guilds and channels have been moved. "
                "Please use `[p]moveignoredchannels` if "
                "you were previously using these functions."
            )
            self.bot.loop.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
            await self.config.version.set("1.1.0")
        if await self.config.version() < "1.2.0":
            msg = _(
                "Delete delay settings have been moved. "
                "Please use `[p]movedeletedelay` if "
                "you were previously using these functions."
            )
            self.bot.loop.create_task(send_to_owners_with_prefix_replaced(self.bot, msg))
            await self.config.version.set("1.2.0")

    @commands.command()
    @commands.is_owner()
    async def moveignoredchannels(self, ctx: commands.Context) -> None:
        """Move ignored channels and servers to core"""
        all_guilds = await self.config.all_guilds()
        all_channels = await self.config.all_channels()
        for guild_id, settings in all_guilds.items():
            await self.bot._config.guild_from_id(guild_id).ignored.set(settings["ignored"])
            await self.config.guild_from_id(guild_id).ignored.clear()
        for channel_id, settings in all_channels.items():
            await self.bot._config.channel_from_id(channel_id).ignored.set(settings["ignored"])
            await self.config.channel_from_id(channel_id).clear()
        await ctx.send(_("Ignored channels and guilds restored."))

    @commands.command()
    @commands.is_owner()
    async def movedeletedelay(self, ctx: commands.Context) -> None:
        """
            Move deletedelay settings to core
        """
        all_guilds = await self.config.all_guilds()
        for guild_id, settings in all_guilds.items():
            await self.bot._config.guild_from_id(guild_id).delete_delay.set(
                settings["delete_delay"]
            )
            await self.config.guild_from_id(guild_id).delete_delay.clear()
        await ctx.send(_("Delete delay settings restored."))
