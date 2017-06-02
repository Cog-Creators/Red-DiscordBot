from discord.ext import commands
from .repo_manager import RepoManager
from .installable import Installable


class RepoName(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        return RepoManager.validate_and_normalize_repo_name(arg)


class InstalledCog(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> dict:
        downloader = ctx.bot.get_cog("Downloader")
        if downloader is None:
            raise commands.CommandError("Downloader not loaded.")

        try:
            return Installable.from_json(downloader.installed_cogs[arg])
        except KeyError as e:
            raise commands.BadArgument(
                "That cog is not installed"
            ) from e
