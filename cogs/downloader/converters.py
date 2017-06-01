from discord.ext import commands
from .repo_manager import RepoManager
from .repo_manager import Repo as RealRepo


class RepoName(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        return RepoManager.validate_and_normalize_repo_name(arg)
