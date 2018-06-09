import discord
from redbot.core import commands
from .installable import Installable


class InstalledCog(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> Installable:
        downloader = ctx.bot.get_cog("Downloader")
        if downloader is None:
            raise commands.CommandError("Downloader not loaded.")

        cog = discord.utils.get(await downloader.installed_cogs(), name=arg)
        if cog is None:
            raise commands.BadArgument("That cog is not installed")

        return cog
