import asyncio
import contextlib
import re
from typing import Tuple, Iterable, Collection, Optional, Set, List

import discord
from redbot.core import _downloader, commands, version_info as red_version_info
from redbot.core._downloader import errors
from redbot.core._downloader.installable import InstalledModule
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import can_user_react_in
from redbot.core.utils.chat_formatting import box, pagify, humanize_list, inline
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .checks import do_install_agreement
from .converters import InstalledCog, Repo
from .log import log

_ = Translator("Downloader", __file__)


DEPRECATION_NOTICE = _(
    "\n**WARNING:** The following repos are using shared libraries"
    " which are marked for removal in the future: {repo_list}.\n"
    " You should inform maintainers of these repos about this message."
)


@cog_i18n(_)
class Downloader(commands.Cog):
    """Install community cogs made by Cog Creators.

    Community cogs, also called third party cogs, are not included
    in the default Red install.

    Community cogs come in repositories. Repos are a group of cogs
    you can install. You always need to add the creator's repository
    using the `[p]repo` command before you can install one or more
    cogs from the creator.
    """

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.already_agreed = False

    async def red_delete_data_for_user(self, **kwargs):
        """Nothing to delete"""
        return

    @staticmethod
    async def send_pagified(target: discord.abc.Messageable, content: str) -> None:
        for page in pagify(content):
            await target.send(page)

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def pipinstall(self, ctx: commands.Context, *deps: str) -> None:
        """
        Install a group of dependencies using pip.

        Examples:
        - `[p]pipinstall bs4`
        - `[p]pipinstall py-cpuinfo psutil`

        Improper usage of this command can break your bot, be careful.

        **Arguments**

        - `<deps...>` The package or packages you wish to install.
        """
        async with ctx.typing():
            success = await _downloader.pip_install(*deps)

        if success:
            await ctx.send(_("Libraries installed.") if len(deps) > 1 else _("Library installed."))
        else:
            await ctx.send(
                _(
                    "Some libraries failed to install. Please check"
                    " your logs for a complete list."
                )
                if len(deps) > 1
                else _(
                    "The library failed to install. Please check your logs for a complete list."
                )
            )

    @commands.group()
    @commands.is_owner()
    async def repo(self, ctx: commands.Context) -> None:
        """Base command for repository management."""
        pass

    @repo.command(name="add")
    async def _repo_add(
        self, ctx: commands.Context, name: str, repo_url: str, branch: str = None
    ) -> None:
        """Add a new repo.

        Examples:
        - `[p]repo add 26-Cogs https://github.com/Twentysix26/x26-Cogs`
        - `[p]repo add Laggrons-Dumb-Cogs https://github.com/retke/Laggrons-Dumb-Cogs v3`

        Repo names can only contain characters A-z, numbers, underscores, hyphens, and dots (but they cannot start or end with a dot).

        The branch will be the default branch if not specified.

        **Arguments**

        - `<name>` The name given to the repo.
        - `<repo_url>` URL to the cog branch. Usually GitHub or GitLab.
        - `[branch]` Optional branch to install cogs from.
        """
        agreed = await do_install_agreement(ctx)
        if not agreed:
            return
        # TODO: verify this in the Downloader APIs
        if name.startswith(".") or name.endswith("."):
            await ctx.send(_("Repo names cannot start or end with a dot."))
            return
        if re.match(r"^[a-zA-Z0-9_\-\.]+$", name) is None:
            await ctx.send(
                _(
                    "Repo names can only contain characters A-z, numbers, underscores, hyphens,"
                    " and dots."
                )
            )
            return
        try:
            async with ctx.typing():
                # noinspection PyTypeChecker
                repo = await _downloader._repo_manager.add_repo(
                    name=name, url=repo_url, branch=branch
                )
        except errors.ExistingGitRepo:
            await ctx.send(
                _("The repo name you provided is already in use. Please choose another name.")
            )
        except errors.AuthenticationError as err:
            await ctx.send(
                _(
                    "Failed to authenticate or repository does not exist."
                    " See logs for more information."
                )
            )
            log.exception(
                "Something went wrong whilst cloning %s (to revision: %s)",
                repo_url,
                branch,
                exc_info=err,
            )

        except errors.CloningError as err:
            await ctx.send(
                _(
                    "Something went wrong during the cloning process."
                    " See logs for more information."
                )
            )
            log.exception(
                "Something went wrong whilst cloning %s (to revision: %s)",
                repo_url,
                branch,
                exc_info=err,
            )
        except OSError:
            log.exception(
                "Something went wrong trying to add repo %s under name %s",
                repo_url,
                name,
            )
            await ctx.send(
                _(
                    "Something went wrong trying to add that repo."
                    " See logs for more information."
                )
            )
        else:
            await ctx.send(_("Repo `{name}` successfully added.").format(name=name))
            if repo.install_msg:
                await ctx.send(
                    repo.install_msg.replace("[p]", ctx.clean_prefix).replace(
                        "[botname]", ctx.me.display_name
                    )
                )

    @repo.command(name="delete", aliases=["remove", "del"], require_var_positional=True)
    async def _repo_del(self, ctx: commands.Context, *repos: Repo) -> None:
        """
        Remove repos and their files.

        Examples:
        - `[p]repo delete 26-Cogs`
        - `[p]repo delete 26-Cogs Laggrons-Dumb-Cogs`

        **Arguments**

        - `<repos...>` The repo or repos to remove.
        """
        for repo in set(repos):
            await _downloader._repo_manager.delete_repo(repo.name)

        await ctx.send(
            (
                _("Successfully deleted repos: ")
                if len(repos) > 1
                else _("Successfully deleted the repo: ")
            )
            + humanize_list([inline(i.name) for i in set(repos)])
        )

    @repo.command(name="list")
    async def _repo_list(self, ctx: commands.Context) -> None:
        """List all installed repos."""
        repos = _downloader._repo_manager.repos
        sorted_repos = sorted(repos, key=lambda r: str.lower(r.name))
        if len(repos) == 0:
            joined = _("There are no repos installed.")
        else:
            if len(repos) > 1:
                joined = _("## Installed Repos\n")
            else:
                joined = _("## Installed Repo\n")
            for repo in sorted_repos:
                joined += "- **{}:** {}\n  - {}\n".format(
                    repo.name,
                    repo.short or "",
                    (
                        f"<{repo.clean_url}>"
                        if repo.clean_url.startswith(("http://", "https://"))
                        else repo.clean_url
                    ),
                )

        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(page)

    @repo.command(name="info")
    async def _repo_info(self, ctx: commands.Context, repo: Repo) -> None:
        """Show information about a repo.

        Example:
        - `[p]repo info 26-Cogs`

        **Arguments**

        - `<repo>` The name of the repo to show info about.
        """
        made_by = ", ".join(repo.author) or _("Missing from info.json")

        information = _("Repo url: {repo_url}\n").format(repo_url=repo.clean_url)
        if repo.branch:
            information += _("Branch: {branch_name}\n").format(branch_name=repo.branch)
        information += _("Made by: {author}\nDescription:\n{description}").format(
            author=made_by, description=repo.description or ""
        )

        msg = _("Information on {repo_name} repo:{information}").format(
            repo_name=inline(repo.name), information=box(information)
        )

        await ctx.send(msg)

    @repo.command(name="update")
    async def _repo_update(self, ctx: commands.Context, *repos: Repo) -> None:
        """Update all repos, or ones of your choosing.

        This will *not* update the cogs installed from those repos.

        Examples:
        - `[p]repo update`
        - `[p]repo update 26-Cogs`
        - `[p]repo update 26-Cogs Laggrons-Dumb-Cogs`

        **Arguments**

        - `[repos...]` The name or names of repos to update. If omitted, all repos are updated.
        """
        async with ctx.typing():
            updated: Set[str]

            updated_repos, failed = await _downloader._repo_manager.update_repos(repos)
            updated = {repo.name for repo in updated_repos}

            if updated:
                message = _("Repo update completed successfully.")
                message += _("\nUpdated: ") + humanize_list(tuple(map(inline, updated)))
            elif not repos:
                message = _("All installed repos are already up to date.")
            else:
                if len(updated_repos) > 1:
                    message = _("These repos are already up to date.")
                else:
                    message = _("This repo is already up to date.")

            if failed:
                message += "\n" + self.format_failed_repos(failed)

        await self.send_pagified(ctx, message)

    @commands.group()
    @commands.is_owner()
    async def cog(self, ctx: commands.Context) -> None:
        """Base command for cog installation management commands."""
        pass

    @cog.command(name="reinstallreqs", hidden=True)
    async def _cog_reinstallreqs(self, ctx: commands.Context) -> None:
        """
        This command should not be used unless Red specifically asks for it.

        This command will reinstall cog requirements and shared libraries for all installed cogs.

        Red might ask the owner to use this when it clears contents of the lib folder
        because of change in minor version of Python.
        """
        async with ctx.typing():
            failed_reqs, failed_libs = await _downloader.reinstall_requirements()

        message = ""
        if failed_reqs:
            message += (
                _("Failed to install requirements: ")
                if len(failed_reqs) > 1
                else _("Failed to install the requirement: ")
            ) + humanize_list(tuple(map(inline, failed_reqs)))
        if failed_libs:
            libnames = [lib.name for lib in failed_libs]
            message += (
                _("\nFailed to install shared libraries: ")
                if len(failed_libs) > 1
                else _("\nFailed to install shared library: ")
            ) + humanize_list(tuple(map(inline, libnames)))
        if message:
            await self.send_pagified(
                ctx,
                _(
                    "Cog requirements and shared libraries for all installed cogs"
                    " have been reinstalled but there were some errors:\n"
                )
                + message,
            )
        else:
            await ctx.send(
                _(
                    "Cog requirements and shared libraries"
                    " for all installed cogs have been reinstalled."
                )
            )

    @cog.command(name="install", usage="<repo> <cogs...>", require_var_positional=True)
    async def _cog_install(self, ctx: commands.Context, repo: Repo, *cog_names: str) -> None:
        """Install a cog from the given repo.

        Examples:
        - `[p]cog install 26-Cogs defender`
        - `[p]cog install Laggrons-Dumb-Cogs say roleinvite`

        **Arguments**

        - `<repo>` The name of the repo to install cogs from.
        - `<cogs...>` The cog or cogs to install.
        """
        await self._cog_installrev(ctx, repo, None, cog_names)

    @cog.command(
        name="installversion", usage="<repo> <revision> <cogs...>", require_var_positional=True
    )
    async def _cog_installversion(
        self, ctx: commands.Context, repo: Repo, revision: str, *cog_names: str
    ) -> None:
        """Install a cog from the specified revision of given repo.

        Revisions are "commit ids" that point to the point in the code when a specific change was made.
        The latest revision can be found in the URL bar for any GitHub repo by [pressing "y" on that repo](https://docs.github.com/en/free-pro-team@latest/github/managing-files-in-a-repository/getting-permanent-links-to-files#press-y-to-permalink-to-a-file-in-a-specific-commit).

        Older revisions can be found in the URL bar by [viewing the commit history of any repo](https://cdn.discordapp.com/attachments/133251234164375552/775760247787749406/unknown.png)

        Example:
        - `[p]cog installversion Broken-Repo e798cc268e199612b1316a3d1f193da0770c7016 cog_name`

        **Arguments**

        - `<repo>` The name of the repo to install cogs from.
        - `<revision>` The revision to install from.
        - `<cogs...>` The cog or cogs to install.
        """
        await self._cog_installrev(ctx, repo, revision, cog_names)

    async def _cog_installrev(
        self, ctx: commands.Context, repo: Repo, rev: Optional[str], cog_names: Iterable[str]
    ) -> None:
        async with ctx.typing():
            try:
                install_result = await _downloader.install_cogs(repo, rev, cog_names)
            except errors.AmbiguousRevision as e:
                msg = _("Error: short sha1 `{rev}` is ambiguous. Possible candidates:\n").format(
                    rev=rev
                )
                for candidate in e.candidates:
                    msg += (
                        f"**{candidate.object_type} {candidate.rev}**"
                        f" - {candidate.description}\n"
                    )
                await self.send_pagified(ctx, msg)
                return
            except errors.UnknownRevision:
                await ctx.send(
                    _("Error: there is no revision `{rev}` in repo `{repo.name}`").format(
                        rev=rev, repo=repo
                    )
                )
                return

            deprecation_notice = ""
            if repo.available_libraries:
                deprecation_notice = DEPRECATION_NOTICE.format(repo_list=inline(repo.name))

            message = self._format_invalid_cogs(repo, install_result)
            if install_result.failed_reqs:
                message += (
                    _("\nFailed to install requirements: ")
                    if len(install_result.failed_reqs) > 1
                    else _("\nFailed to install the requirement: ")
                ) + humanize_list(tuple(map(inline, install_result.failed_reqs)))
            if install_result.failed_libs:
                libnames = [inline(lib.name) for lib in install_result.failed_libs]
                message = (
                    (
                        _("\nFailed to install shared libraries for `{repo.name}` repo: ")
                        if len(libnames) > 1
                        else _("\nFailed to install shared library for `{repo.name}` repo: ")
                    ).format(repo=repo)
                    + humanize_list(libnames)
                    + message
                )
            if install_result.failed_cogs:
                cognames = [inline(cog.name) for cog in install_result.failed_cogs]
                message = (
                    (
                        _("\nFailed to install cogs: ")
                        if len(install_result.failed_cogs) > 1
                        else _("\nFailed to install the cog: ")
                    )
                    + humanize_list(cognames)
                    + message
                )
            if install_result.installed_cogs:
                cognames = [inline(cog.name) for cog in install_result.installed_cogs]
                message = (
                    (
                        _("Successfully installed cogs: ")
                        if len(install_result.installed_cogs) > 1
                        else _("Successfully installed the cog: ")
                    )
                    + humanize_list(cognames)
                    + (
                        _(
                            "\nThese cogs are now pinned and won't get updated automatically."
                            " To change this, use `{prefix}cog unpin <cog>`"
                        ).format(prefix=ctx.clean_prefix)
                        if rev is not None
                        else ""
                    )
                    + _(
                        "\nYou can load them using {command_1}."
                        " To see end user data statements, you can use {command_2}."
                    ).format(
                        command_1=inline(f"{ctx.clean_prefix}load <cogs...>"),
                        command_2=inline(f"{ctx.clean_prefix}cog info <repo> <cog>"),
                    )
                    + message
                )
        # "---" added to separate cog install messages from Downloader's message
        await self.send_pagified(ctx, f"{message}{deprecation_notice}\n---")
        for cog in install_result.installed_cogs:
            if cog.install_msg:
                await ctx.send(
                    cog.install_msg.replace("[p]", ctx.clean_prefix).replace(
                        "[botname]", ctx.me.display_name
                    )
                )

    @cog.command(name="uninstall", require_var_positional=True)
    async def _cog_uninstall(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Uninstall cogs.

        You may only uninstall cogs which were previously installed
        by Downloader.

        Examples:
        - `[p]cog uninstall defender`
        - `[p]cog uninstall say roleinvite`

        **Arguments**

        - `<cogs...>` The cog or cogs to uninstall.
        """
        async with ctx.typing():
            uninstalled_cogs, failed_cogs = await _downloader.uninstall_cogs(*cogs)

            message = ""
            if uninstalled_cogs:
                message += (
                    _("Successfully uninstalled cogs: ")
                    if len(uninstalled_cogs) > 1
                    else _("Successfully uninstalled the cog: ")
                ) + humanize_list(tuple(map(inline, uninstalled_cogs)))
            if failed_cogs:
                if len(failed_cogs) > 1:
                    message += (
                        _(
                            "\nDownloader has removed these cogs from the installed cogs list"
                            " but it wasn't able to find their files: "
                        )
                        + humanize_list(tuple(map(inline, failed_cogs)))
                        + _(
                            "\nThey were most likely removed without using {command_1}.\n"
                            "You may need to remove those files manually if the cogs are still usable."
                            " If so, ensure the cogs have been unloaded with {command_2}."
                        ).format(
                            command_1=inline(f"{ctx.clean_prefix}cog uninstall"),
                            command_2=inline(f"{ctx.clean_prefix}unload {' '.join(failed_cogs)}"),
                        )
                    )
                else:
                    message += (
                        _(
                            "\nDownloader has removed this cog from the installed cogs list"
                            " but it wasn't able to find its files: "
                        )
                        + inline(failed_cogs[0])
                        + _(
                            "\nIt was most likely removed without using {command_1}.\n"
                            "You may need to remove those files manually if the cog is still usable."
                            " If so, ensure the cog has been unloaded with {command_2}."
                        ).format(
                            command_1=inline(f"{ctx.clean_prefix}cog uninstall"),
                            command_2=inline(f"{ctx.clean_prefix}unload {failed_cogs[0]}"),
                        )
                    )
        await self.send_pagified(ctx, message)

    @cog.command(name="pin", require_var_positional=True)
    async def _cog_pin(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Pin cogs - this will lock cogs on their current version.

        Examples:
        - `[p]cog pin defender`
        - `[p]cog pin outdated_cog1 outdated_cog2`

        **Arguments**

        - `<cogs...>` The cog or cogs to pin. Must already be installed.
        """
        pinned, already_pinned = await _downloader.pin_cogs(*cogs)
        message = ""
        if pinned:
            cognames = [inline(cog.name) for cog in pinned]
            message += (
                _("Pinned cogs: ") if len(pinned) > 1 else _("Pinned cog: ")
            ) + humanize_list(cognames)
        if already_pinned:
            cognames = [inline(cog.name) for cog in already_pinned]
            message += (
                _("\nThese cogs were already pinned: ")
                if len(already_pinned) > 1
                else _("\nThis cog was already pinned: ")
            ) + humanize_list(cognames)
        await self.send_pagified(ctx, message)

    @cog.command(name="unpin", require_var_positional=True)
    async def _cog_unpin(self, ctx: commands.Context, *cogs: InstalledCog) -> None:
        """Unpin cogs - this will remove the update lock from those cogs.

        Examples:
        - `[p]cog unpin defender`
        - `[p]cog unpin updated_cog1 updated_cog2`

        **Arguments**

        - `<cogs...>` The cog or cogs to unpin. Must already be installed and pinned."""
        unpinned, not_pinned = await _downloader.unpin_cogs(*cogs)
        message = ""
        if unpinned:
            cognames = [inline(cog.name) for cog in unpinned]
            message += (
                _("Unpinned cogs: ") if len(unpinned) > 1 else _("Unpinned cog: ")
            ) + humanize_list(cognames)
        if not_pinned:
            cognames = [inline(cog.name) for cog in not_pinned]
            message += (
                _("\nThese cogs weren't pinned: ")
                if len(not_pinned) > 1
                else _("\nThis cog was already not pinned: ")
            ) + humanize_list(cognames)
        await self.send_pagified(ctx, message)

    @cog.command(name="listpinned")
    async def _cog_listpinned(self, ctx: commands.Context):
        """List currently pinned cogs."""
        installed = await _downloader.installed_cogs()
        pinned_list = sorted(
            [cog for cog in installed if cog.pinned], key=lambda cog: cog.name.lower()
        )
        if pinned_list:
            message = "\n".join(
                f"({inline(cog.commit[:7] or _('unknown'))}) {cog.name}" for cog in pinned_list
            )
        else:
            message = _("None.")
        if await ctx.embed_requested():
            embed = discord.Embed(color=(await ctx.embed_colour()))
            for page in pagify(message, page_length=900):
                name = _("(continued)") if page.startswith("\n") else _("Pinned Cogs:")
                embed.add_field(name=name, value=page, inline=False)
            await ctx.send(embed=embed)
        else:
            for page in pagify(message, page_length=1900):
                if not page.startswith("\n"):
                    page = _("Pinned Cogs: \n") + page
                await ctx.send(page)

    @cog.command(name="checkforupdates")
    async def _cog_checkforupdates(self, ctx: commands.Context) -> None:
        """
        Check for available cog updates (including pinned cogs).

        This command doesn't update cogs, it only checks for updates.
        Use `[p]cog update` to update cogs.
        """

        async with ctx.typing():
            update_check_result = await _downloader.check_cog_updates()
            filter_message = self._format_incompatible_cogs(update_check_result)

            message = ""
            if update_check_result.outdated_cogs:
                cognames = [cog.name for cog in update_check_result.outdated_cogs]
                message += (
                    _("These cogs can be updated: ")
                    if len(cognames) > 1
                    else _("This cog can be updated: ")
                ) + humanize_list(tuple(map(inline, cognames)))
            if update_check_result.outdated_libs:
                libnames = [cog.name for cog in update_check_result.outdated_libs]
                message += (
                    _("\nThese shared libraries can be updated: ")
                    if len(libnames) > 1
                    else _("\nThis shared library can be updated: ")
                ) + humanize_list(tuple(map(inline, libnames)))
            if not update_check_result.updates_available and filter_message:
                message += _("No cogs can be updated.")
            message += filter_message

            if not message:
                message = _("All installed cogs are up to date.")

            if update_check_result.failed_repos:
                message += "\n" + self.format_failed_repos(update_check_result.failed_repos)

        await self.send_pagified(ctx, message)

    @cog.command(name="update")
    async def _cog_update(
        self, ctx: commands.Context, reload: Optional[bool], *cogs: InstalledCog
    ) -> None:
        """Update all cogs, or ones of your choosing.

        Examples:
        - `[p]cog update`
        - `[p]cog update True`
        - `[p]cog update defender`
        - `[p]cog update True defender`

        **Arguments**

        - `[reload]` Whether to reload cogs immediately after update or not.
        - `[cogs...]` The cog or cogs to update. If omitted, all cogs are updated.
        """
        if reload:
            ctx.assume_yes = True
        await self._cog_update_logic(ctx, cogs=cogs)

    @cog.command(name="updateallfromrepos", require_var_positional=True)
    async def _cog_updateallfromrepos(
        self, ctx: commands.Context, reload: Optional[bool], *repos: Repo
    ) -> None:
        """Update all cogs from repos of your choosing.

        Examples:
        - `[p]cog updateallfromrepos 26-Cogs`
        - `[p]cog updateallfromrepos True 26-Cogs`
        - `[p]cog updateallfromrepos Laggrons-Dumb-Cogs 26-Cogs`

        **Arguments**

        - `[reload]` Whether to reload cogs immediately after update or not.
        - `<repos...>` The repo or repos to update all cogs from.
        """
        if reload:
            ctx.assume_yes = True
        await self._cog_update_logic(ctx, repos=repos)

    @cog.command(name="updatetoversion")
    async def _cog_updatetoversion(
        self,
        ctx: commands.Context,
        reload: Optional[bool],
        repo: Repo,
        revision: str,
        *cogs: InstalledCog,
    ) -> None:
        """Update all cogs, or ones of your choosing to chosen revision of one repo.

        Note that update doesn't mean downgrade and therefore `revision`
        has to be newer than the version that cog currently has installed. If you want to
        downgrade the cog, uninstall and install it again.

        See `[p]cog installversion` for an explanation of `revision`.

        Examples:
        - `[p]cog updatetoversion Broken-Repo e798cc268e199612b1316a3d1f193da0770c7016 cog_name`
        - `[p]cog updatetoversion True Broken-Repo 6107c0770ad391f1d3a6131b216991e862cc897e cog_name`

        **Arguments**

        - `[reload]` Whether to reload cogs immediately after update or not.
        - `<repo>` The repo or repos to update all cogs from.
        - `<revision>` The revision to update to.
        - `[cogs...]` The cog or cogs to update.
        """
        if reload:
            ctx.assume_yes = True
        await self._cog_update_logic(ctx, repo=repo, rev=revision, cogs=cogs)

    async def _cog_update_logic(
        self,
        ctx: commands.Context,
        *,
        repo: Optional[Repo] = None,
        repos: Optional[List[Repo]] = None,
        rev: Optional[str] = None,
        cogs: Optional[List[InstalledModule]] = None,
    ) -> None:
        async with ctx.typing():
            if repo is not None:
                try:
                    update_result = await _downloader.update_repo_cogs(repo, cogs, rev=rev)
                except errors.AmbiguousRevision as e:
                    msg = _(
                        "Error: short sha1 `{rev}` is ambiguous. Possible candidates:\n"
                    ).format(rev=rev)
                    for candidate in e.candidates:
                        msg += (
                            f"**{candidate.object_type} {candidate.rev}**"
                            f" - {candidate.description}\n"
                        )
                    await self.send_pagified(ctx, msg)
                    return
                except errors.UnknownRevision:
                    message = _(
                        "Error: there is no revision `{rev}` in repo `{repo.name}`"
                    ).format(rev=rev, repo=repo)
                    await ctx.send(message)
                    return
            else:
                update_result = await _downloader.update_cogs(cogs=cogs, repos=repos)

            message = ""
            if not update_result.checked_cogs:
                message += _("There were no cogs to check.")
            elif update_result.updates_available:
                message = await self._format_cog_update_result(ctx, update_result)
            else:
                if repos:
                    message += _("Cogs from provided repos are already up to date.")
                elif repo:
                    if cogs:
                        message += _("Provided cogs are already up to date with this revision.")
                    else:
                        message += _(
                            "Cogs from provided repo are already up to date with this revision."
                        )
                else:
                    if cogs:
                        message += _("Provided cogs are already up to date.")
                    else:
                        message += _("All installed cogs are already up to date.")

            if update_result.pinned_cogs:
                cognames = [cog.name for cog in update_result.pinned_cogs]
                message += (
                    _("\nThese cogs are pinned and therefore weren't checked: ")
                    if len(cognames) > 1
                    else _("\nThis cog is pinned and therefore wasn't checked: ")
                ) + humanize_list(tuple(map(inline, cognames)))

            message += self._format_incompatible_cogs(update_result)

        if update_result.failed_repos:
            message += "\n" + self.format_failed_repos(update_result.failed_repos)

        repos_with_libs = {
            inline(module.repo.name)
            for module in update_result.updated_modules
            if module.repo.available_libraries
        }
        if repos_with_libs:
            message += DEPRECATION_NOTICE.format(repo_list=humanize_list(list(repos_with_libs)))

        await self.send_pagified(ctx, message)

        if update_result.updated_cogs:
            await self._ask_for_cog_reload(ctx, update_result.updated_cogs)

    @cog.command(name="list")
    async def _cog_list(self, ctx: commands.Context, repo: Repo) -> None:
        """List all available cogs from a single repo.

        Example:
        - `[p]cog list 26-Cogs`

        **Arguments**

        - `<repo>` The repo to list cogs from.
        """
        sort_function = lambda x: x.name.lower()
        all_installed_cogs = await _downloader.installed_cogs()
        installed_cogs_in_repo = [cog for cog in all_installed_cogs if cog.repo_name == repo.name]
        installed_str = "\n".join(
            "- {}{}".format(i.name, ": {}".format(i.short) if i.short else "")
            for i in sorted(installed_cogs_in_repo, key=sort_function)
        )

        if len(installed_cogs_in_repo) > 1:
            installed_str = _("# Installed Cogs\n{text}").format(text=installed_str)
        elif installed_cogs_in_repo:
            installed_str = _("# Installed Cog\n{text}").format(text=installed_str)

        available_cogs = [
            cog for cog in repo.available_cogs if not (cog.hidden or cog in installed_cogs_in_repo)
        ]
        available_str = "\n".join(
            "+ {}{}".format(cog.name, ": {}".format(cog.short) if cog.short else "")
            for cog in sorted(available_cogs, key=sort_function)
        )

        if not available_str:
            cogs = _("> Available Cogs\nNo cogs are available.")
        elif len(available_cogs) > 1:
            cogs = _("> Available Cogs\n{text}").format(text=available_str)
        else:
            cogs = _("> Available Cog\n{text}").format(text=available_str)
        cogs = cogs + "\n\n" + installed_str
        for page in pagify(cogs, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="markdown"))

    @cog.command(name="info", usage="<repo> <cog>")
    async def _cog_info(self, ctx: commands.Context, repo: Repo, cog_name: str) -> None:
        """List information about a single cog.

        Example:
        - `[p]cog info 26-Cogs defender`

        **Arguments**

        - `<repo>` The repo to get cog info from.
        - `<cog>` The cog to get info on.
        """
        cog = discord.utils.get(repo.available_cogs, name=cog_name)
        if cog is None:
            await ctx.send(
                _("There is no cog `{cog_name}` in the repo `{repo.name}`").format(
                    cog_name=cog_name, repo=repo
                )
            )
            return

        msg = _(
            "Information on {cog_name}:\n"
            "{description}\n\n"
            "End user data statement:\n"
            "{end_user_data_statement}\n\n"
            "Made by: {author}\n"
            "Requirements: {requirements}"
        ).format(
            cog_name=cog.name,
            description=cog.description or "",
            end_user_data_statement=(
                cog.end_user_data_statement
                or _("Author of the cog didn't provide end user data statement.")
            ),
            author=", ".join(cog.author) or _("Missing from info.json"),
            requirements=", ".join(cog.requirements) or "None",
        )
        for page in pagify(msg):
            await ctx.send(box(page))

    def _format_invalid_cogs(
        self, repo: Repo, install_result: _downloader.CogInstallResult
    ) -> str:
        message = ""
        if install_result.unavailable_cogs:
            message = (
                _("\nCouldn't find these cogs in {repo.name}: ")
                if len(install_result.unavailable_cogs) > 1
                else _("\nCouldn't find this cog in {repo.name}: ")
            ).format(repo=repo) + humanize_list(install_result.unavailable_cogs)
        if install_result.already_installed:
            message += (
                _("\nThese cogs were already installed: ")
                if len(install_result.already_installed) > 1
                else _("\nThis cog was already installed: ")
            ) + humanize_list([cog.name for cog in install_result.already_installed])
        if install_result.name_already_used:
            message += (
                _("\nSome cogs with these names are already installed from different repos: ")
                if len(install_result.name_already_used) > 1
                else _("\nCog with this name is already installed from a different repo: ")
            ) + humanize_list([cog.name for cog in install_result.name_already_used])
        # TODO: resolve typing issue
        add_to_message = self._format_incompatible_cogs(install_result)
        if add_to_message:
            return f"{message}{add_to_message}"
        return message

    def _format_incompatible_cogs(
        self, update_check_result: _downloader.CogUpdateCheckResult
    ) -> str:
        message = ""
        if update_check_result.incompatible_python_version:
            message += (
                _("\nThese cogs require higher python version than you have: ")
                if len(update_check_result.incompatible_python_version)
                else _("\nThis cog requires higher python version than you have: ")
            ) + humanize_list(
                [
                    inline(cog.name)
                    + _(" (Minimum: {min_version})").format(
                        min_version=".".join([str(n) for n in cog.min_python_version])
                    )
                    for cog in update_check_result.incompatible_python_version
                ]
            )
        if update_check_result.incompatible_bot_version:
            message += (
                _(
                    "\nThese cogs require different Red version"
                    " than you currently have ({current_version}): "
                )
                if len(update_check_result.incompatible_bot_version) > 1
                else _(
                    "\nThis cog requires different Red version than you currently "
                    "have ({current_version}): "
                )
            ).format(current_version=red_version_info) + humanize_list(
                [
                    inline(cog.name)
                    + _(" (Minimum: {min_version}").format(min_version=cog.min_bot_version)
                    + (
                        ""
                        if cog.min_bot_version > cog.max_bot_version
                        else _(", at most: {max_version}").format(max_version=cog.max_bot_version)
                    )
                    + ")"
                    for cog in update_check_result.incompatible_bot_version
                ]
            )

        return message

    async def _format_cog_update_result(
        self, ctx: commands.Context, update_result: _downloader.CogUpdateResult
    ) -> str:
        current_cog_versions_map = {cog.name: cog for cog in update_result.checked_cogs}
        if update_result.failed_reqs:
            return (
                _("Failed to install requirements: ")
                if len(update_result.failed_reqs) > 1
                else _("Failed to install the requirement: ")
            ) + humanize_list(tuple(map(inline, update_result.failed_reqs)))

        message = _("Cog update completed successfully.")

        if update_result.updated_cogs:
            cogs_with_changed_eud_statement = set()
            for cog in update_result.updated_cogs:
                current_eud_statement = current_cog_versions_map[cog.name].end_user_data_statement
                if current_eud_statement != cog.end_user_data_statement:
                    cogs_with_changed_eud_statement.add(cog.name)
            message += _("\nUpdated: ") + humanize_list(
                [inline(cog.name) for cog in update_result.updated_cogs]
            )
            if cogs_with_changed_eud_statement:
                if len(cogs_with_changed_eud_statement) > 1:
                    message += (
                        _("\nEnd user data statements of these cogs have changed: ")
                        + humanize_list(tuple(map(inline, cogs_with_changed_eud_statement)))
                        + _("\nYou can use {command} to see the updated statements.\n").format(
                            command=inline(f"{ctx.clean_prefix}cog info <repo> <cog>")
                        )
                    )
                else:
                    message += (
                        _("\nEnd user data statement of this cog has changed:")
                        + inline(next(iter(cogs_with_changed_eud_statement)))
                        + _("\nYou can use {command} to see the updated statement.\n").format(
                            command=inline(f"{ctx.clean_prefix}cog info <repo> <cog>")
                        )
                    )
            # If the bot has any slash commands enabled, warn them to sync
            enabled_slash = await self.bot.list_enabled_app_commands()
            if any(enabled_slash.values()):
                message += _(
                    "\nYou may need to resync your slash commands with `{prefix}slash sync`."
                ).format(prefix=ctx.prefix)
        if update_result.failed_cogs:
            cognames = [cog.name for cog in update_result.failed_cogs]
            message += (
                _("\nFailed to update cogs: ")
                if len(update_result.failed_cogs) > 1
                else _("\nFailed to update cog: ")
            ) + humanize_list(tuple(map(inline, cognames)))
        if not update_result.outdated_cogs:
            message = _("No cogs were updated.")
        if update_result.updated_libs:
            message += (
                _(
                    "\nSome shared libraries were updated, you should restart the bot "
                    "to bring the changes into effect."
                )
                if len(update_result.updated_libs) > 1
                else _(
                    "\nA shared library was updated, you should restart the "
                    "bot to bring the changes into effect."
                )
            )
        if update_result.failed_libs:
            libnames = [lib.name for lib in update_result.failed_libs]
            message += (
                _("\nFailed to install shared libraries: ")
                if len(update_result.failed_libs) > 1
                else _("\nFailed to install shared library: ")
            ) + humanize_list(tuple(map(inline, libnames)))
        return message

    async def _ask_for_cog_reload(
        self, ctx: commands.Context, updated_cogs: Tuple[InstalledModule, ...]
    ) -> None:
        updated_cognames = {cog.name for cog in updated_cogs}
        updated_cognames &= ctx.bot.extensions.keys()  # only reload loaded cogs
        if not updated_cognames:
            await ctx.send(_("None of the updated cogs were previously loaded. Update complete."))
            return

        if not ctx.assume_yes:
            message = (
                _("Would you like to reload the updated cogs?")
                if len(updated_cognames) > 1
                else _("Would you like to reload the updated cog?")
            )
            can_react = can_user_react_in(ctx.me, ctx.channel)
            if not can_react:
                message += " (yes/no)"
            query: discord.Message = await ctx.send(message)
            if can_react:
                # noinspection PyAsyncCall
                start_adding_reactions(query, ReactionPredicate.YES_OR_NO_EMOJIS)
                pred = ReactionPredicate.yes_or_no(query, ctx.author)
                event = "reaction_add"
            else:
                pred = MessagePredicate.yes_or_no(ctx)
                event = "message"
            try:
                await ctx.bot.wait_for(event, check=pred, timeout=30)
            except asyncio.TimeoutError:
                with contextlib.suppress(discord.NotFound):
                    await query.delete()
                return

            if not pred.result:
                if can_react:
                    with contextlib.suppress(discord.NotFound):
                        await query.delete()
                else:
                    await ctx.send(_("OK then."))
                return
            else:
                if can_react:
                    with contextlib.suppress(discord.Forbidden):
                        await query.clear_reactions()

        await ctx.invoke(ctx.bot.get_cog("Core").reload, *updated_cognames)

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
        return splitted[0]

    @commands.command()
    async def findcog(self, ctx: commands.Context, command_name: str) -> None:
        """Find which cog a command comes from.

        This will only work with loaded cogs.

        Example:
        - `[p]findcog ping`

        **Arguments**

        - `<command_name>` The command to search for.
        """
        command = ctx.bot.all_commands.get(command_name)

        if command is None:
            await ctx.send(_("That command doesn't seem to exist."))
            return

        # Check if in installed cogs
        cog = command.cog
        if cog:
            cog_pkg_name = self.cog_name_from_instance(cog)
            installed, cog_installable = await _downloader.is_installed(cog_pkg_name)
            if installed:
                made_by = (
                    humanize_list(cog_installable.author)
                    if cog_installable.author
                    else _("Missing from info.json")
                )
                repo_url = (
                    _("Missing from installed repos")
                    if cog_installable.repo is None
                    else cog_installable.repo.clean_url
                )
                repo_name = (
                    _("Missing from installed repos")
                    if cog_installable.repo is None
                    else cog_installable.repo.name
                )
                cog_pkg_name = cog_installable.name
            elif cog.__module__.startswith("redbot."):  # core commands or core cog
                made_by = "Cog Creators"
                repo_url = "https://github.com/Cog-Creators/Red-DiscordBot"
                module_fragments = cog.__module__.split(".")
                if module_fragments[1] == "core":
                    cog_pkg_name = "N/A - Built-in commands"
                else:
                    cog_pkg_name = module_fragments[2]
                repo_name = "Red-DiscordBot"
            else:  # assume not installed via downloader
                made_by = _("Unknown")
                repo_url = _("None - this cog wasn't installed via downloader")
                repo_name = _("Unknown")
            cog_name = cog.__class__.__name__
        else:
            msg = _("This command is not provided by a cog.")
            await ctx.send(msg)
            return

        if await ctx.embed_requested():
            embed = discord.Embed(color=(await ctx.embed_colour()))
            embed.add_field(name=_("Command:"), value=command_name, inline=False)
            embed.add_field(name=_("Cog package name:"), value=cog_pkg_name, inline=True)
            embed.add_field(name=_("Cog name:"), value=cog_name, inline=True)
            embed.add_field(name=_("Made by:"), value=made_by, inline=False)
            embed.add_field(name=_("Repo name:"), value=repo_name, inline=False)
            embed.add_field(name=_("Repo URL:"), value=repo_url, inline=False)
            if installed and cog_installable.repo is not None and cog_installable.repo.branch:
                embed.add_field(
                    name=_("Repo branch:"), value=cog_installable.repo.branch, inline=False
                )
            await ctx.send(embed=embed)

        else:
            msg = _(
                "Command:          {command}\n"
                "Cog package name: {cog_pkg}\n"
                "Cog name:         {cog}\n"
                "Made by:          {author}\n"
                "Repo name:        {repo_name}\n"
                "Repo URL:         {repo_url}\n"
            ).format(
                command=command_name,
                cog_pkg=cog_pkg_name,
                cog=cog_name,
                author=made_by,
                repo_url=repo_url,
                repo_name=repo_name,
            )
            if installed and cog_installable.repo is not None and cog_installable.repo.branch:
                msg += _("Repo branch: {branch_name}\n").format(
                    branch_name=cog_installable.repo.branch
                )
            await ctx.send(box(msg))

    @staticmethod
    def format_failed_repos(failed: Collection[str]) -> str:
        """Format collection of ``Repo.name``'s into failed message.

        Parameters
        ----------
        failed : Collection
            Collection of ``Repo.name``

        Returns
        -------
        str
            formatted message
        """

        message = (
            _("Failed to update the following repositories:")
            if len(failed) > 1
            else _("Failed to update the following repository:")
        )
        message += " " + humanize_list(tuple(map(inline, failed))) + "\n"
        message += _(
            "The repository's branch might have been removed or"
            " the repository is no longer accessible at set url."
            " See logs for more information."
        )
        return message
