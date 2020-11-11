import discord
from redbot.core import commands
from redbot.core.i18n import Translator
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
            raise commands.BadArgument(
                _("Cog `{cog_name}` is not installed.").format(cog_name=arg)
            )

        return cog
