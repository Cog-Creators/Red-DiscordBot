import asyncio
import re
from abc import ABC
from collections import defaultdict
from typing import List, Tuple

import discord
from redbot.core import Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from .casetypes import CASETYPES
from .events import Events
from .kickban import KickBanMixin
from .movetocore import MoveToCore
from .mutes import MuteMixin
from .names import ModInfo
from .slowmode import Slowmode
from .settings import ModSettings

_ = T_ = Translator("Mod", __file__)

__version__ = "1.1.0"


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
    MoveToCore,
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

        self.settings = Config.get_conf(self, 4961522000, force_registration=True)
        self.settings.register_global(**self.default_global_settings)
        self.settings.register_guild(**self.default_guild_settings)
        self.settings.register_channel(**self.default_channel_settings)
        self.settings.register_member(**self.default_member_settings)
        self.settings.register_user(**self.default_user_settings)
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
        if not await self.settings.version():
            guild_dict = await self.settings.all_guilds()
            for guild_id, info in guild_dict.items():
                delete_repeats = info.get("delete_repeats", False)
                if delete_repeats:
                    val = 3
                else:
                    val = -1
                await self.settings.guild(discord.Object(id=guild_id)).delete_repeats.set(val)
            await self.settings.version.set("1.0.0")  # set version of last update
        if await self.settings.version() < "1.1.0":
            prefixes = await self.bot.get_valid_prefixes()
            prefix = re.sub(rf"<@!?{self.bot.user.id}>", f"@{self.bot.user.name}", prefixes[0])
            msg = _(
                "Ignored guilds and channels have been moved. "
                "Please use `{prefix}moveignoredchannels` if "
                "you were previously using these functions."
            ).format(prefix=prefix)
            self.bot.loop.create_task(self.bot.send_to_owners(msg))
            await self.settings.version.set(__version__)

    @commands.command()
    @commands.is_owner()
    async def moveignoredchannels(self, ctx: commands.Context) -> None:
        """Move ignored channels and servers to core"""
        all_guilds = await self.settings.all_guilds()
        all_channels = await self.settings.all_channels()
        for guild_id, settings in all_guilds.items():
            await self.bot._config.guild_from_id(guild_id).ignored.set(settings["ignored"])
            await self.settings.guild_from_id(guild_id).ignored.clear()
        for channel_id, settings in all_channels.items():
            await self.bot._config.channel_from_id(channel_id).ignored.set(settings["ignored"])
            await self.settings.channel_from_id(channel_id).clear()
        await ctx.send(_("Ignored channels and guilds restored."))
