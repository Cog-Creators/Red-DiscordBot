import discord
from redbot.core import _downloader, commands
from redbot.core.i18n import Translator
from redbot.core._downloader.installable import InstalledModule
from redbot.core._downloader.repo_manager import Repo as _Repo

_ = Translator("Koala", __file__)


class InstalledCog(InstalledModule):
    @classmethod
    async def convert(cls, ctx: commands.Context, arg: str) -> InstalledModule:
        cog = discord.utils.get(await _downloader.installed_cogs(), name=arg)
        if cog is None:
            raise commands.BadArgument(
                _("Cog `{cog_name}` is not installed.").format(cog_name=arg)
            )

        return cog


class Repo(_Repo):
    @classmethod
    async def convert(cls, ctx: commands.Context, argument: str) -> _Repo:
        poss_repo = _downloader._repo_manager.get_repo(argument)
        if poss_repo is None:
            raise commands.BadArgument(
                _('Repo by the name "{repo_name}" does not exist.').format(repo_name=argument)
            )
        return poss_repo
