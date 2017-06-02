from typing import MutableMapping, Tuple

import discord
from discord.ext import commands
from pathlib import Path

from core import Config
from core.bot import Red
from core import checks
from core.utils.chat_formatting import box

from .repo_manager import RepoManager, Repo
from .installable import Installable
from .converters import RepoName, InstalledCogData
from .log import log
from .errors import CloningError, ExistingGitRepo


class Downloader:

    COG_PATH = Path.cwd() / "cogs"
    LIB_PATH = Path.cwd() / "lib"
    SHAREDLIB_PATH = LIB_PATH / "cog_shared"
    SHAREDLIB_INIT = SHAREDLIB_PATH / "__init__.py"

    def __init__(self, bot: Red):
        self.bot = bot

        self.conf = Config.get_conf(self, unique_identifier=998240343,
                                    force_registration=True)

        self.conf.register_global(
            repos={},
            installed=[]
        )

        self.LIB_PATH.mkdir(parents=True, exist_ok=True)
        self.SHAREDLIB_PATH.mkdir(parents=True, exist_ok=True)
        if not self.SHAREDLIB_INIT.exists():
            with self.SHAREDLIB_INIT.open(mode='w') as f:
                pass

        self._repo_manager = RepoManager(self.conf)

    @property
    def installed_cogs(self) -> Tuple[Installable]:
        """
        Returns the dictionary mapping cog name to install location
            and repo name.
        :return:
        """
        installed = self.conf.installed()
        # noinspection PyTypeChecker
        return tuple(Installable.from_json(v) for v in installed)

    async def _add_to_installed(self, cog: Installable):
        """
        Marks a cog as installed.
        :param cog:
        :return:
        """
        installed = self.conf.installed()
        installed.append(cog.to_json())
        await self.conf.set("installed", list(set(installed)))

    async def _reinstall_cogs(self, cogs: Tuple[Installable]) -> Tuple[Installable]:
        """
        Installs a list of cogs, used when updating.
        :param cogs:
        :return: Any cogs that failed to copy
        """
        failed = []
        for cog in cogs:
            if not await cog.copy_to(self.COG_PATH):
                failed.append(cog)

        # noinspection PyTypeChecker
        return tuple(failed)

    async def _reinstall_libraries(self, cogs: Tuple[Installable]) -> Tuple[Installable]:
        """
        Reinstalls any shared libraries from the repos of cogs that
            were updated.
        :param cogs:
        :return: Any libraries that failed to copy
        """
        repo_names = set(cog.repo_name for cog in cogs)
        unfiltered_repos = (self._repo_manager.get_repo(r) for r in repo_names)
        repos = filter(lambda r: r is not None, unfiltered_repos)

        failed = []

        for repo in repos:
            if not await repo.install_libraries(target_dir=self.SHAREDLIB_PATH):
                failed.extend(repo.available_libraries)

        # noinspection PyTypeChecker
        return tuple(failed)

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

    @repo.command(name="del")
    async def _repo_del(self, ctx, repo_name: Repo):
        """
        Removes a repo from Downloader and its' files.
        :param repo_name: Repo name in Downloader
        """
        await self._repo_manager.delete_repo(repo_name.name)

        await ctx.send("The repo `{}` has been deleted successfully.".format(repo_name.name))

    @repo.command(name="list")
    async def _repo_list(self, ctx):
        """
        Lists all installed repos.
        """
        repos = self._repo_manager.get_all_repo_names()
        joined = "Installed Repos:\n" + "\n".join(["+ " + r for r in repos])

        await ctx.send(box(joined, lang="diff"))

    @commands.group()
    @checks.is_owner()
    async def cog(self, ctx):
        """
        Command group for managing installable Cogs.
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @cog.command(name="install")
    async def _cog_install(self, ctx, repo_name: Repo, cog_name: str):
        """
        Installs a cog from the given repo.
        :param repo_name:
        :param cog_name: Cog name available from `[p]cog list <repo_name>`
        """
        cog = discord.utils.get(repo_name.available_cogs, name=cog_name)
        await repo_name.install_cog(cog, self.COG_PATH)

        await self._add_to_installed(cog)

        await repo_name.install_libraries(self.SHAREDLIB_PATH)

        await ctx.send("`{}` cog successfully installed.".format(cog_name))

    @cog.command(name="uninstall")
    async def _cog_uninstall(self, ctx, cog_name: InstalledCogData):
        """
        Allows you to uninstall cogs that were previously installed
            through Downloader.
        :param cog_name:
        """
        raise NotImplementedError()

    @cog.command(name="update")
    async def _cog_update(self, ctx, cog_name: InstalledCogData=None):
        """
        Updates all cogs or one of your choosing.
        :param cog_name:
        """
        if cog_name is None:
            updated = await self._repo_manager.update_all_repos()
            installed_cogs = set(self.installed_cogs)
            updated_cogs = set(cog for repo in updated.keys() for cog in repo.available_cogs)

            installed_and_updated = updated_cogs & installed_cogs

            # noinspection PyTypeChecker
            await self._reinstall_cogs(installed_and_updated)

            # noinspection PyTypeChecker
            await self._reinstall_libraries(installed_and_updated)
        await ctx.send("Cog update completed successfully.")

    @cog.command(name="list")
    async def _cog_list(self, ctx, repo_name: Repo):
        """
        Lists all available cogs from a single repo.
        :param repo_name: Repo name available from `[p]repo list`
        """
        cogs = repo_name.available_cogs
        cogs = "Available Cogs:\n" + "\n".join(
            ["+ {}: {}".format(c.name, c.short or "") for c in cogs])

        await ctx.send(box(cogs, lang="diff"))

    @cog.command(name="info")
    async def _cog_info(self, ctx, repo_name: Repo, cog_name: str):
        """
        Lists information about a single cog.
        :param repo_name:
        :param cog_name:
        """
        cog = discord.utils.get(repo_name.available_cogs, name=cog_name)
        if cog is None:
            await ctx.send("There is no cog `{}` in the repo `{}`".format(
                cog_name, repo_name.name
            ))
            return

        msg = "Information on {}:\n{}".format(cog.name, cog.description or "")
        await ctx.send(box(msg))
