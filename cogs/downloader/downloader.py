from discord.ext import commands
from core import Config
from core.bot import Red
from core import checks

from .repo_manager import RepoManager
from .converters import RepoName, Repo
from .log import log
from .errors import CloningError, ExistingGitRepo


class Downloader:
    def __init__(self, bot: Red):
        self.bot = bot

        self.conf = Config.get_conf(self, unique_identifier=998240343,
                                    force_registration=True)

        self.conf.register_global(
            repos={}
        )

        self._repo_manager = RepoManager(self.conf)

    @commands.group()
    @checks.is_owner()
    async def repo(self, ctx):
        """
        Command group for managing Downloader repos.
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @repo.command(name="add")
    async def _repo_add(self, ctx, name: RepoName, repo_url: str, branch: str="master"):
        """
        Add a new repo to Downloader.
        :param name: Name that must follow python variable naming rules and
            contain only characters A-Z and numbers 0-9 and _
        :param repo_url: Clone url for the cog repo
        """
        try:
            # noinspection PyTypeChecker
            await self._repo_manager.add_repo(
                name=name,
                url=repo_url,
                branch=branch
            )
        except ExistingGitRepo:
            await ctx.send("That git repo has already been added under another name.")
        except CloningError:
            await ctx.send("Something went wrong during the cloning process.")
            log.exception("Something went wrong during the cloning process.")
        else:
            await ctx.send("Repo `{}` successfully added.".format(name))

    # noinspection PyUnresolvedReferences
    @repo.command(name="del")
    async def _repo_del(self, ctx, repo_name: Repo):
        """
        Removes a repo from Downloader and its' files.
        :param name: Repo name in Downloader
        """
        await self._repo_manager.delete_repo(repo_name.name)

        await ctx.send("The repo `{}` has been deleted successfully.".format(repo_name.name))

    @repo.command(name="list")
    async def _repo_list(self, ctx):
        """
        Lists all installed repos.
        """
        raise NotImplementedError()

    @commands.group()
    @checks.is_owner()
    async def cog(self, ctx):
        """
        Command group for managing installable Cogs.
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @cog.command(name="install")
    async def _cog_install(self, ctx, repo_name: str, cog_name: str):
        """
        Installs a cog from the given repo.
        :param repo_name:
        :param cog_name: Cog name available from `[p]cog list <repo_name>`
        """
        raise NotImplementedError()

    @cog.command(name="list")
    async def _cog_list(self, ctx, repo_name: str):
        """
        Lists all available cogs from a single repo.
        :param repo_name: Repo name available from `[p]repo list`
        """
        raise NotImplementedError()

    @cog.command(name="info")
    async def _cog_info(self, ctx, repo_name: str, cog_name: str):
        """
        Lists information about a single cog.
        :param repo_name:
        :param cog_name:
        """
        raise NotImplementedError()
