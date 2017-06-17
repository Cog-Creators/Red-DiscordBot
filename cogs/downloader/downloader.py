import os
import shutil
from typing import Tuple

import discord
from discord.ext import commands
from pathlib import Path
from sys import path as syspath

from core import Config
from core.bot import Red
from core import checks
from core.utils.chat_formatting import box

from .repo_manager import RepoManager, Repo
from .installable import Installable
from .converters import RepoName, InstalledCog
from .log import log
from .errors import CloningError, ExistingGitRepo
from .checks import install_agreement


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

        self.already_agreed = False

        self.LIB_PATH.mkdir(parents=True, exist_ok=True)
        self.SHAREDLIB_PATH.mkdir(parents=True, exist_ok=True)
        if not self.SHAREDLIB_INIT.exists():
            with self.SHAREDLIB_INIT.open(mode='w') as _:
                pass

        if str(self.LIB_PATH) not in syspath:
            syspath.insert(1, str(self.LIB_PATH))

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
        cog_json = cog.to_json()

        if cog_json not in installed:
            installed.append(cog_json)
            await self.conf.set("installed", installed)

    async def _remove_from_installed(self, cog: Installable):
        """
        Removes a cog from the saved list of installed cogs.
        :param cog:
        :return:
        """
        installed = self.conf.installed()
        cog_json = cog.to_json()

        if cog_json in installed:
            installed.remove(cog_json)
            await self.conf.set("installed", installed)

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

    async def _reinstall_requirements(self, cogs: Tuple[Installable]) -> bool:
        """
        Reinstalls requirements for given cogs that have been updated.
            Returns a bool that indicates if all requirement installations
            were successful.
        :param cogs:
        :return:
        """

        # Reduces requirements to a single list with no repeats
        requirements = set(r for c in cogs for r in c.requirements)
        repo_names = self._repo_manager.get_all_repo_names()
        repos = [(self._repo_manager.get_repo(rn), []) for rn in repo_names]

        # This for loop distributes the requirements across all repos
        # which will allow us to concurrently install requirements
        for i, req in enumerate(requirements):
            repo_index = i % len(repos)
            repos[repo_index][1].append(req)

        has_reqs = list(filter(lambda item: len(item[1]) > 0, repos))

        ret = True
        for repo, reqs in has_reqs:
            for req in reqs:
                # noinspection PyTypeChecker
                ret = ret and await repo.install_raw_requirements([req, ], self.LIB_PATH)
        return ret

    @staticmethod
    async def _delete_cog(target: Path):
        """
        Removes an (installed) cog.
        :param target: Path pointing to an existing file or directory
        :return:
        """
        if not target.exists():
            return

        if target.is_dir():
            shutil.rmtree(str(target))
        elif target.is_file():
            os.remove(str(target))

    @commands.group()
    @checks.is_owner()
    async def repo(self, ctx):
        """
        Command group for managing Downloader repos.
        """
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @repo.command(name="add")
    @install_agreement()
    async def _repo_add(self, ctx, name: RepoName, repo_url: str, branch: str=None):
        """
        Add a new repo to Downloader.

        Name can only contain characters A-z, numbers and underscore
        Branch will default to master if not specified
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

    @repo.command(name="delete")
    async def _repo_del(self, ctx, repo_name: Repo):
        """
        Removes a repo from Downloader and its' files.
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
        """
        cog = discord.utils.get(repo_name.available_cogs, name=cog_name)
        if cog is None:
            await ctx.send("Error, there is no cog by the name of"
                           " `{}` in the `{}` repo.".format(cog_name, repo_name.name))
            return

        if not await repo_name.install_requirements(cog, self.LIB_PATH):
            await ctx.send("Failed to install the required libraries for"
                           " `{}`: `{}`".format(cog.name, cog.requirements))
            return

        await repo_name.install_cog(cog, self.COG_PATH)

        await self._add_to_installed(cog)

        await repo_name.install_libraries(self.SHAREDLIB_PATH)

        await ctx.send("`{}` cog successfully installed.".format(cog_name))

    @cog.command(name="uninstall")
    async def _cog_uninstall(self, ctx, cog_name: InstalledCog):
        """
        Allows you to uninstall cogs that were previously installed
            through Downloader.
        """
        # noinspection PyUnresolvedReferences,PyProtectedMember
        real_name = cog_name.name

        poss_installed_path = self.COG_PATH / real_name
        if poss_installed_path.exists():
            await self._delete_cog(poss_installed_path)
            # noinspection PyTypeChecker
            await self._remove_from_installed(cog_name)
            await ctx.send("`{}` was successfully removed.".format(real_name))
        else:
            await ctx.send("That cog was installed but can no longer"
                           " be located. You may need to remove it's"
                           " files manually if it is still usable.")

    @cog.command(name="update")
    async def _cog_update(self, ctx, cog_name: InstalledCog=None):
        """
        Updates all cogs or one of your choosing.
        """
        if cog_name is None:
            updated = await self._repo_manager.update_all_repos()
            installed_cogs = set(self.installed_cogs)
            updated_cogs = set(cog for repo in updated.keys() for cog in repo.available_cogs)

            installed_and_updated = updated_cogs & installed_cogs

            # noinspection PyTypeChecker
            await self._reinstall_requirements(installed_and_updated)

            # noinspection PyTypeChecker
            await self._reinstall_cogs(installed_and_updated)

            # noinspection PyTypeChecker
            await self._reinstall_libraries(installed_and_updated)
        await ctx.send("Cog update completed successfully.")

    @cog.command(name="list")
    async def _cog_list(self, ctx, repo_name: Repo):
        """
        Lists all available cogs from a single repo.
        """
        cogs = repo_name.available_cogs
        cogs = "Available Cogs:\n" + "\n".join(
            ["+ {}: {}".format(c.name, c.short or "") for c in cogs])

        await ctx.send(box(cogs, lang="diff"))

    @cog.command(name="info")
    async def _cog_info(self, ctx, repo_name: Repo, cog_name: str):
        """
        Lists information about a single cog.
        """
        cog = discord.utils.get(repo_name.available_cogs, name=cog_name)
        if cog is None:
            await ctx.send("There is no cog `{}` in the repo `{}`".format(
                cog_name, repo_name.name
            ))
            return

        msg = "Information on {}:\n{}".format(cog.name, cog.description or "")
        await ctx.send(box(msg))
