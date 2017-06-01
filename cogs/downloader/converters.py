from discord.ext import commands
from .repo_manager import RepoManager


class RepoName(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str):
        return RepoManager.validate_and_normalize_repo_name(arg)


class Repo(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        downloader_cog = ctx.bot.get_cog("Downloader")
        if downloader_cog is None:
            raise RuntimeError("No Downloader cog found.")

        # noinspection PyProtectedMember
        repo_manager = downloader_cog._repo_manager
        poss_repo = repo_manager.get_repo(argument)
        if poss_repo is None:
            raise ValueError("Repo by the name {} does not exist.".format(argument))
        return poss_repo