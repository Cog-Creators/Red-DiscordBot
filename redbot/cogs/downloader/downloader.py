import asyncio
import contextlib
import os
import re
import shutil
import sys
from pathlib import Path
from sys import path as syspath
from typing import Tuple, Union, Iterable, Optional, Dict, Set
from collections import defaultdict

import discord
from redbot.core import checks, commands, Config, version_info as red_version_info
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, pagify, humanize_list, inline
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from . import errors
from .checks import do_install_agreement
from .converters import InstalledCog
from .installable import InstallableType, Installable, InstalledModule
from .log import log
from .repo_manager import RepoManager, Repo

_ = Translator("Downloader", __file__)


@cog_i18n(_)
class Downloader(commands.Cog):
    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot

        self.conf = Config.get_conf(self, identifier=998240343, force_registration=True)

        self.conf.register_global(installed_cogs={}, installed_libraries={})

        self.already_agreed = False

        self.LIB_PATH = cog_data_path(self) / "lib"
        self.SHAREDLIB_PATH = self.LIB_PATH / "cog_shared"
        self.SHAREDLIB_INIT = self.SHAREDLIB_PATH / "__init__.py"

        self.SHAREDLIB_PATH.mkdir(parents=True, exist_ok=True)
        if not self.SHAREDLIB_INIT.exists():
            with self.SHAREDLIB_INIT.open(mode="w", encoding="utf-8") as _:
                pass

        self._repo_manager = RepoManager()

    async def initialize(self):
        await self._repo_manager.initialize()
        await self._maybe_update_conf_format()

    async def _maybe_update_conf_format(self):
        # backwards compatibility conf format update
        old_conf = await self.conf.get_raw("installed", default=[])
        if not old_conf:
            return
        async with self.conf.installed_cogs() as new_cog_conf:
            for cog_json in old_conf:
                repo_name = cog_json["repo_name"]
                module_name = cog_json["cog_name"]
                if repo_name not in new_cog_conf:
                    new_cog_conf[repo_name] = {}
                new_cog_conf[repo_name][module_name] = {
                    "repo_name": repo_name,
                    "module_name": module_name,
                    "commit": "",
                    "pinned": False,
                }
        await self.conf.clear_raw("installed")
        # no reliable way to get installed libraries (i.a. missing repo name)
        # but it only helps `[p]cog update` run faster so it's not an issue

    async def cog_install_path(self):
        """Get the current cog install path.

        Returns
        -------
        pathlib.Path
            The default cog install path.

        """
        return await self.bot._cog_mgr.install_path()

    async def installed_cogs(self) -> Tuple[InstalledModule]:
        """Get info on installed cogs.

        Returns
        -------
        `tuple` of `InstalledModule`
            All installed cogs.

        """
        installed = await self.conf.installed_cogs()
        # noinspection PyTypeChecker
        return tuple(
            InstalledModule.from_json(cog_json, self._repo_manager)
            for repo_json in installed.values()
            for cog_json in repo_json.values()
        )

    async def installed_libraries(self) -> Tuple[InstalledModule]:
        """Get info on installed shared libraries.

        Returns
        -------
        `tuple` of `InstalledModule`
            All installed shared libraries.

        """
        installed = await self.conf.installed_libraries()
        # noinspection PyTypeChecker
        return tuple(
            InstalledModule.from_json(lib_json, self._repo_manager)
            for repo_json in installed.values()
            for lib_json in repo_json.values()
        )

    async def installed_modules(self) -> Tuple[InstalledModule]:
        """Get info on installed cogs and shared libraries.

        Returns
        -------
        `tuple` of `InstalledModule`
            All installed cogs and shared libraries.

        """
        return await self.installed_cogs() + await self.installed_libraries()

    async def _add_to_installed(self, modules: Iterable[InstalledModule]):
        """Mark modules as installed.

        Parameters
        ----------
        modules : `list` of `InstalledModule`
            The modules to check off.

        """
        installed_cogs = await self.conf.installed_cogs()
        installed_libraries = await self.conf.installed_libraries()
        for module in modules:
            if module.type == InstallableType.COG:
                installed = installed_cogs
            elif module.type == InstallableType.SHARED_LIBRARY:
                installed = installed_libraries
            else:
                continue
            module_json = module.to_json()
            if module.repo_name not in installed:
                installed[module.repo_name] = {}
            installed[module.repo_name][module.name] = module_json

        await self.conf.installed_cogs.set(installed_cogs)
        await self.conf.installed_libraries.set(installed_libraries)

    async def _remove_from_installed(self, modules: Iterable[InstalledModule]):
        """Remove modules from the saved list
        of installed modules (corresponding to type of module).

        Parameters
        ----------
        modules : `list` of `InstalledModule`
            The modules to remove.

        """
        installed_cogs = await self.conf.installed_cogs()
        installed_libraries = await self.conf.installed_libraries()
        for module in modules:
            if module.type == InstallableType.COG:
                installed = installed_cogs
            elif module.type == InstallableType.SHARED_LIBRARY:
                installed = installed_libraries
            else:
                continue
            with contextlib.suppress(KeyError):
                installed[module.repo_name].pop(module.name)

        await self.conf.installed_cogs.set(installed_cogs)
        await self.conf.installed_libraries.set(installed_libraries)

    async def _available_updates(
        self, cogs: Iterable[InstalledModule]
    ) -> Tuple[Tuple[Installable], Tuple[Installable]]:
        """
        Get cogs and libraries which can be updated.

        Parameters
        ----------
        cogs : `list` of `InstalledModule`
            List of cogs, which should be checked against the updates.

        Returns
        -------
        tuple
            2-tuple of cogs and libraries which can be updated.

        """
        repo_names = set(module.repo_name for module in cogs)
        repos = {r: self._repo_manager.get_repo(r) for r in repo_names}
        installed_libraries = await self.installed_libraries()

        modules = set()
        cogs_to_update = set()
        libraries_to_update = set()
        for repo in repos.values():
            for lib in repo.available_libraries:
                try:
                    index = installed_libraries.index(lib)
                except ValueError:
                    libraries_to_update.append(lib)
                else:
                    modules.add(installed_libraries[index])
        for cog in cogs:
            repo = repos[cog.repo_name]
            if repo is None:
                continue
            if cog.commit:
                modules.add(cog)
                continue
            available_cogs = repo.available_cogs
            with contextlib.suppress(ValueError):
                index = available_cogs.index(cog)
                cogs_to_update.add(available_cogs[index])

        # Reduces diff requests to a single dict with no repeats
        hashes: Dict[Tuple[Repo, str], Set[InstalledModule]] = defaultdict(set)
        for module in modules:
            hashes[(repos[module.repo_name], module.commit)].add(module)

        for (repo, old_hash), modules_to_check in hashes.items():
            for module in await repo.get_modified_modules(old_hash):
                if module not in modules_to_check:
                    continue
                if module.type == InstallableType.COG:
                    cogs_to_update.add(module)
                elif module.type == InstallableType.SHARED_LIBRARY:
                    libraries_to_update.add(module)

        return (tuple(cogs_to_update), tuple(libraries_to_update))

    async def _reinstall_cogs(
        self, cogs: Iterable[Installable]
    ) -> Tuple[Tuple[InstalledModule], Tuple[Installable]]:
        """Installs a list of cogs, used when updating.

        Parameters
        ----------
        cogs : `list` of `Installable`
            Cogs to reinstall.
        Returns
        -------
        tuple
            2-tuple of installed and failed cogs.
        """
        installed = []
        failed = []
        for cog in cogs:
            if await cog.copy_to(await self.cog_install_path()):
                installed.append(InstalledModule.from_installable(cog))
            else:
                failed.append(cog)

        # noinspection PyTypeChecker
        return (tuple(installed), tuple(failed))

    async def _reinstall_libraries(
        self, libraries: Iterable[Installable]
    ) -> Tuple[Tuple[InstalledModule], Tuple[Installable]]:
        """Installs a list of shared libraries, used when updating.

        Parameters
        ----------
        libraries : `list` of `Installable`
            Libraries to reinstall.
        Returns
        -------
        tuple
            2-tuple of installed and failed libraries.
        """
        repo_names = set(lib.repo_name for lib in libraries)
        repos = {r: (self._repo_manager.get_repo(r), set()) for r in repo_names}

        for lib in libraries:
            repos[lib.repo_name].add(lib)

        all_installed = []
        all_failed = []
        for repo, libs in repos.values():
            installed, failed = await repo.install_libraries(
                target_dir=self.SHAREDLIB_PATH, req_target_dir=self.LIB_PATH, libraries=libs
            )
            all_installed += installed
            all_failed += failed

        # noinspection PyTypeChecker
        return (tuple(all_installed), tuple(all_failed))

    async def _reinstall_requirements(self, cogs: Iterable[Installable]) -> bool:
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
                ret = ret and await repo.install_raw_requirements([req], self.LIB_PATH)
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

    @commands.command()
    @checks.is_owner()
    async def pipinstall(self, ctx, *deps: str):
        """Install a group of dependencies using pip."""
        if not deps:
            return await ctx.send_help()
        repo = Repo("", "", "", "", Path.cwd(), loop=ctx.bot.loop)
        async with ctx.typing():
            success = await repo.install_raw_requirements(deps, self.LIB_PATH)

        if success:
            await ctx.send(_("Libraries installed."))
        else:
            await ctx.send(
                _(
                    "Some libraries failed to install. Please check"
                    " your logs for a complete list."
                )
            )

    @commands.group()
    @checks.is_owner()
    async def repo(self, ctx):
        """Repo management commands."""
        pass

    @repo.command(name="add")
    async def _repo_add(self, ctx, name: str, repo_url: str, branch: str = None):
        """Add a new repo.

        Repo names can only contain characters A-z, numbers, underscores, and hyphens.
        The branch will be the default branch if not specified.
        """
        agreed = await do_install_agreement(ctx)
        if not agreed:
            return
        if re.match("^[a-zA-Z0-9_\-]*$", name) is None:
            await ctx.send(
                _("Repo names can only contain characters A-z, numbers, underscores, and hyphens.")
            )
            return
        try:
            # noinspection PyTypeChecker
            repo = await self._repo_manager.add_repo(name=name, url=repo_url, branch=branch)
        except errors.ExistingGitRepo:
            await ctx.send(_("That git repo has already been added under another name."))
        except errors.CloningError as err:
            await ctx.send(_("Something went wrong during the cloning process."))
            log.exception(
                "Something went wrong whilst cloning %s (to revision: %s)",
                repo_url,
                branch,
                exc_info=err,
            )
        except OSError:
            await ctx.send(
                _(
                    "Something went wrong trying to add that repo. Your repo name might have an invalid character."
                )
            )
        else:
            await ctx.send(_("Repo `{name}` successfully added.").format(name=name))
            if repo.install_msg is not None:
                await ctx.send(repo.install_msg.replace("[p]", ctx.prefix))

    @repo.command(name="delete", aliases=["remove", "del"], usage="<repo_name>")
    async def _repo_del(self, ctx, repo: Repo):
        """Remove a repo and its files."""
        await self._repo_manager.delete_repo(repo.name)

        await ctx.send(
            _("The repo `{repo.name}` has been deleted successfully.").format(repo=repo)
        )

    @repo.command(name="list")
    async def _repo_list(self, ctx):
        """List all installed repos."""
        repos = self._repo_manager.get_all_repo_names()
        repos = sorted(repos, key=str.lower)
        joined = _("Installed Repos:\n\n")
        for repo_name in repos:
            repo = self._repo_manager.get_repo(repo_name)
            joined += "+ {}: {}\n".format(repo.name, repo.short or "")

        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @repo.command(name="info", usage="<repo_name>")
    async def _repo_info(self, ctx, repo: Repo):
        """Show information about a repo."""
        if repo is None:
            await ctx.send(_("Repo `{repo.name}` not found.").format(repo=repo))
            return

        msg = _("Information on {repo.name}:\n{description}").format(
            repo=repo, description=repo.description or ""
        )
        await ctx.send(box(msg))

    @repo.command(name="update")
    async def _repo_update(self, ctx, repos: commands.Greedy[Repo] = []):
        """Update all repos, or ones of your choosing."""
        async with ctx.typing():
            if not repos:
                updated = await self._repo_manager.update_all_repos()
            else:
                updated = set()
                for repo in repos:
                    old, new = await repo.update()
                    if old != new:
                        updated.add(repo.name)

            if updated:
                message = _("Repo update completed successfully.")
                message += _("\nUpdated: ") + humanize_list(tuple(map(inline, updated)))
            elif repos is None:
                await ctx.send(_("All installed repos are already up to date."))
                return
            else:
                await ctx.send(_("These repos are already up to date."))
                return
        await ctx.send(message)

    @commands.group()
    @checks.is_owner()
    async def cog(self, ctx):
        """Cog installation management commands."""
        pass

    @cog.command(name="install", usage="<repo_name> <cog_name> [revision]")
    async def _cog_install(self, ctx, repo: Repo, cog_name: str, rev: Optional[str] = None):
        """Install a cog from the given repo."""
        commit = None
        if rev is not None:
            try:
                commit = await repo._get_full_sha1(rev)
            except errors.UnknownRevision:
                await ctx.send(
                    _("Error: there is no revision `{rev}` in repo `{repo.name}`").format(
                        rev=rev, repo=repo
                    )
                )
                return

        async with repo.checkout(commit):
            cog: Installable = discord.utils.get(repo.available_cogs, name=cog_name)
            if cog is None:
                await ctx.send(
                    _(
                        "Error: there is no cog by the name of "
                        "`{cog_name}` in the `{repo.name}` repo."
                    ).format(cog_name=cog_name, repo=repo)
                )
                return
            if cog.min_python_version > sys.version_info:
                await ctx.send(
                    _(
                        "This cog requires at least python version {version}, aborting install."
                    ).format(version=".".join([str(n) for n in cog.min_python_version]))
                )
                return
            ignore_max = cog.min_bot_version > cog.max_bot_version
            if (
                cog.min_bot_version > red_version_info
                or not ignore_max
                and cog.max_bot_version < red_version_info
            ):
                await ctx.send(
                    _("This cog requires at least Red version {min_version}").format(
                        min_version=cog.min_bot_version
                    )
                    + (
                        ""
                        if ignore_max
                        else _(" and at most {max_version}").format(
                            max_version=cog.max_bot_version
                        )
                    )
                    + _(", but you have {current_version}, aborting install.").format(
                        current_version=red_version_info
                    )
                )
                return

            if not await repo.install_requirements(cog, self.LIB_PATH):
                libraries = humanize_list(tuple(map(inline, cog.requirements)))
                await ctx.send(
                    _(
                        "Failed to install the required libraries for `{cog_name}`: `{libraries}`"
                    ).format(cog_name=cog.name, libraries=libraries)
                )
                return
            try:
                installed_cog = await repo.install_cog(cog, await self.cog_install_path())
            except errors.CopyingError:
                await ctx.send(
                    _("Failed to copy `{cog_name}` cog files.").format(cog_name=cog.name)
                )
                return

        installed_libs, failed_libs = await repo.install_libraries(
            target_dir=self.SHAREDLIB_PATH, req_target_dir=self.LIB_PATH
        )
        await self._add_to_installed([installed_cog] + list(installed_libs))
        message = ""
        if failed_libs:
            libnames = {l.name for l in failed_libs}
            message += _("Failed to install shared libraries for `{cog_name}`: ") + humanize_list(
                tuple(map(inline, libnames))
            )
        message += _(
            "Cog `{cog_name}` successfully installed. "
            "You can load it with `{prefix}load {cog_name}`"
        ).format(cog_name=cog_name, prefix=ctx.prefix)
        await ctx.send(message)
        if cog.install_msg:
            await ctx.send(cog.install_msg.replace("[p]", ctx.prefix))

    @cog.command(name="uninstall", usage="<cogs>")
    async def _cog_uninstall(self, ctx, cogs: commands.Greedy[InstalledCog]):
        """Uninstall cogs.

        You may only uninstall cogs which were previously installed
        by Downloader.
        """
        if not cogs:
            return await ctx.send_help()
        async with ctx.typing():
            uninstalled_cogs = []
            failed_cogs = []
            for cog in set(cogs):
                real_name = cog.name

                poss_installed_path = (await self.cog_install_path()) / real_name
                if poss_installed_path.exists():
                    with contextlib.suppress(commands.ExtensionNotLoaded):
                        ctx.bot.unload_extension(real_name)
                    await self._delete_cog(poss_installed_path)
                    uninstalled_cogs.append(inline(real_name))
                else:
                    failed_cogs.append(real_name)
            await self._remove_from_installed(cogs)

            message = ""
            if uninstalled_cogs:
                message += _("Successfully uninstalled cogs: ") + humanize_list(uninstalled_cogs)
            if failed_cogs:
                message += (
                    _("\nThese cog were installed but can no longer be located: ")
                    + humanize_list(tuple(map(inline, failed_cogs)))
                    + _(
                        "\nYou may need to remove their files manually if they are still usable."
                        " Also make sure you've unloaded those cogs with `{prefix}unload {cogs}`."
                    ).format(prefix=ctx.prefix, cogs=" ".join(failed_cogs))
                )
        await ctx.send(message)

    @cog.command(name="pin", usage="<cog_name>")
    async def _cog_pin(self, ctx, cog: InstalledCog):
        """Pin a cog - this will lock cog on its current version."""
        if cog.pinned:
            return await ctx.send(
                _("Cog `{cog_name}` is already pinned.").format(cog_name=cog.name)
            )
        cog.pinned = True
        await self._add_to_installed([cog])
        await ctx.send(_("Cog `{cog_name}` has been pinned."))

    @cog.command(name="unpin", usage="<cog_name>")
    async def _cog_unpin(self, ctx, cog: InstalledCog):
        """Unpin a cog - this will remove update lock from cog."""
        if not cog.pinned:
            return await ctx.send(_("Cog `{cog_name}` isn't pinned.").format(cog_name=cog.name))
        cog.pinned = False
        await self._add_to_installed([cog])
        await ctx.send(_("Cog `{cog_name}` has been unpinned."))

    @cog.command(name="update")
    async def _cog_update(self, ctx, cogs: commands.Greedy[InstalledCog] = []):
        """Update all cogs, or ones of your choosing."""
        pinned_cogs = None
        installed_cogs = set(await self.installed_cogs())

        async with ctx.typing():
            if not cogs:
                await self._repo_manager.update_all_repos()
                cogs_to_check = set(self._repo_manager.get_all_cogs())
            else:
                cogs = set(cogs)
                repos = {cog.repo_name for cog in cogs}
                available_cogs = []
                for repo_name in repos:
                    with contextlib.suppress(KeyError):  # Thrown if the repo no longer exists
                        repo, __ = await self._repo_manager.update_repo(repo_name)
                        available_cogs += repo.available_cogs
                cogs_to_check = set(available_cogs) & cogs

            cogs_to_check &= installed_cogs
            pinned_cogs = {cog for cog in cogs_to_check if cog.pinned}
            cogs_to_check -= pinned_cogs
            cogs_to_update, libs_to_update = await self._available_updates(cogs_to_check)

            updates_available = cogs_to_update or libs_to_update
            message = ""
            if updates_available:
                await self._reinstall_requirements(cogs_to_update)
                installed_cogs, failed_cogs = await self._reinstall_cogs(cogs_to_update)
                installed_libs, failed_libs = await self._reinstall_libraries(libs_to_update)
                await self._add_to_installed(installed_cogs + installed_libs)
                message += _("Cog update completed successfully.")

                if installed_cogs:
                    cognames = {c.name for c in installed_cogs}
                    message += _("\nUpdated: ") + humanize_list(tuple(map(inline, cognames)))
                if failed_cogs:
                    cognames = {c.name for c in failed_cogs}
                    message += _("\nFailed to update cogs: ") + humanize_list(
                        tuple(map(inline, cognames))
                    )
                if not cogs_to_update:
                    message += _("\nNo cogs were updated, but some shared libraries were.")
                if failed_libs:
                    libnames = {l.name for l in failed_libs}
                    message += _("Failed to install shared libraries: ") + humanize_list(
                        tuple(map(inline, libnames))
                    )
            else:
                message += _("All installed cogs are already up to date.")
            if pinned_cogs:
                message += _(
                    "\nThese cogs are pinned and therefore weren't checked: "
                ) + humanize_list(tuple(map(inline, pinned_cogs)))
        await ctx.send(message)
        if not updates_available:
            return

        cognames &= set(ctx.bot.extensions.keys())  # only reload loaded cogs
        if not cognames:
            return await ctx.send(
                _("None of the updated cogs were previously loaded. Update complete.")
            )

        if not ctx.assume_yes:
            message = _("Would you like to reload the updated cogs?")
            can_react = ctx.channel.permissions_for(ctx.me).add_reactions
            if not can_react:
                message += " (y/n)"
            query: discord.Message = await ctx.send(message)
            if can_react:
                # noinspection PyAsyncCall
                start_adding_reactions(query, ReactionPredicate.YES_OR_NO_EMOJIS, ctx.bot.loop)
                pred = ReactionPredicate.yes_or_no(query, ctx.author)
                event = "reaction_add"
            else:
                pred = MessagePredicate.yes_or_no(ctx)
                event = "message"
            try:
                await ctx.bot.wait_for(event, check=pred, timeout=30)
            except asyncio.TimeoutError:
                await query.delete()
                return

            if not pred.result:
                if can_react:
                    await query.delete()
                else:
                    await ctx.send(_("OK then."))
                return
            else:
                if can_react:
                    with contextlib.suppress(discord.Forbidden):
                        await query.clear_reactions()

        await ctx.invoke(ctx.bot.get_cog("Core").reload, *cognames)

    @cog.command(name="list", usage="<repo_name>")
    async def _cog_list(self, ctx, repo: Repo):
        """List all available cogs from a single repo."""
        installed = await self.installed_cogs()
        installed_str = ""
        if installed:
            installed_str = _("Installed Cogs:\n") + "\n".join(
                [
                    "- {}{}".format(i.name, ": {}".format(i.short) if i.short else "")
                    for i in installed
                    if i.repo_name == repo.name
                ]
            )
        cogs = repo.available_cogs
        cogs = _("Available Cogs:\n") + "\n".join(
            [
                "+ {}: {}".format(c.name, c.short or "")
                for c in cogs
                if not (c.hidden or c in installed)
            ]
        )
        cogs = cogs + "\n\n" + installed_str
        for page in pagify(cogs, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @cog.command(name="info", usage="<repo_name> <cog_name>")
    async def _cog_info(self, ctx, repo: Repo, cog_name: str):
        """List information about a single cog."""
        cog = discord.utils.get(repo.available_cogs, name=cog_name)
        if cog is None:
            await ctx.send(
                _("There is no cog `{cog_name}` in the repo `{repo.name}`").format(
                    cog_name=cog_name, repo=repo
                )
            )
            return

        msg = _(
            "Information on {cog_name}:\n{description}\n\nRequirements: {requirements}"
        ).format(
            cog_name=cog.name,
            description=cog.description or "",
            requirements=", ".join(cog.requirements) or "None",
        )
        await ctx.send(box(msg))

    async def is_installed(
        self, cog_name: str
    ) -> Union[Tuple[bool, InstalledModule], Tuple[bool, None]]:
        """Check to see if a cog has been installed through Downloader.

        Parameters
        ----------
        cog_name : str
            The name of the cog to check for.

        Returns
        -------
        `tuple` of (`bool`, `InstalledModule`)
            :code:`(True, InstalledModule)` if the cog is installed, else
            :code:`(False, None)`.

        """
        for installed_cog in await self.installed_cogs():
            if installed_cog.name == cog_name:
                return True, installed_cog
        return False, None

    def format_findcog_info(
        self, command_name: str, cog_installable: Union[Installable, object] = None
    ) -> str:
        """Format a cog's info for output to discord.

        Parameters
        ----------
        command_name : str
            Name of the command which belongs to the cog.
        cog_installable : `Installable` or `object`
            Can be an `Installable` instance or a Cog instance.

        Returns
        -------
        str
            A formatted message for the user.

        """
        if isinstance(cog_installable, Installable):
            made_by = ", ".join(cog_installable.author) or _("Missing from info.json")
            repo = self._repo_manager.get_repo(cog_installable.repo_name)
            repo_url = _("Missing from installed repos") if repo is None else repo.url
            cog_name = cog_installable.name
        else:
            made_by = "26 & co."
            repo_url = "https://github.com/Cog-Creators/Red-DiscordBot"
            cog_name = cog_installable.__class__.__name__

        msg = _("Command: {command}\nMade by: {author}\nRepo: {repo}\nCog name: {cog}")

        return msg.format(command=command_name, author=made_by, repo=repo_url, cog=cog_name)

    def cog_name_from_instance(self, instance: object) -> str:
        """Determines the cog name that Downloader knows from the cog instance.

        Probably.

        Parameters
        ----------
        instance : object
            The cog instance.

        Returns
        -------
        str
            The name of the cog according to Downloader..

        """
        splitted = instance.__module__.split(".")
        return splitted[-2]

    @commands.command()
    async def findcog(self, ctx: commands.Context, command_name: str):
        """Find which cog a command comes from.

        This will only work with loaded cogs.
        """
        command = ctx.bot.all_commands.get(command_name)

        if command is None:
            await ctx.send(_("That command doesn't seem to exist."))
            return

        # Check if in installed cogs
        cog = command.cog
        if cog:
            cog_name = self.cog_name_from_instance(cog)
            installed, cog_installable = await self.is_installed(cog_name)
            if installed:
                msg = self.format_findcog_info(command_name, cog_installable)
            else:
                # Assume it's in a base cog
                msg = self.format_findcog_info(command_name, cog)
        else:
            msg = _("This command is not provided by a cog.")

        await ctx.send(box(msg))
