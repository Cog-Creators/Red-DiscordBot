# -*- coding: utf-8 -*-
# Red Dependencies
import discord

# Red Imports
from redbot.core import commands
from redbot.core.i18n import Translator

# Red Relative Imports
from .installable import InstalledModule

_ = Translator("Koala", __file__)


class InstalledCog(InstalledModule):
    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str) -> InstalledModule:
        downloader = ctx.bot.get_cog("Downloader")
        if downloader is None:
            raise commands.CommandError(_("No Downloader cog found."))

        cog = discord.utils.get(await downloader.installed_cogs(), name=arg)
        if cog is None:
            raise commands.BadArgument(_("That cog is not installed"))

        return cog
