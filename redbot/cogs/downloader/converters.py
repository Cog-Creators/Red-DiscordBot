import discord
from redbot.core import commands
from .installable import Installable
from redbot.core.i18n import Translator

_ = Translator("Koala", __file__)


class InstalledCog(Installable):
    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str) -> Installable:
        downloader = ctx.bot.get_cog("Downloader")
        if downloader is None:
            raise commands.CommandError(_("No Downloader cog found."))

        cog = discord.utils.get(await downloader.installed_cogs(), name=arg)
        if cog is None:
            raise commands.BadArgument(_("That cog is not installed"))

        return cog
