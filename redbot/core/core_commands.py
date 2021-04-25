import asyncio
import contextlib
import datetime
import importlib
import itertools
import keyword
import logging
import io
import random
from copy import copy

import markdown
import os
import re
import sys
import platform
import getpass
import pip
import traceback
from pathlib import Path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.commands import GuildConverter
from string import ascii_letters, digits
from typing import TYPE_CHECKING, Union, Tuple, List, Optional, Iterable, Sequence, Dict, Set

import aiohttp
import discord
from babel import Locale as BabelLocale, UnknownLocaleError
from redbot.core.data_manager import storage_type
from redbot.core.utils.chat_formatting import box, pagify

from . import (
    __version__,
    version_info as red_version_info,
    checks,
    commands,
    errors,
    i18n,
)
from .utils import AsyncIter
from .utils._internal_utils import fetch_latest_red_version_info, is_sudo_enabled, timed_unsu
from .utils.predicates import MessagePredicate
from .utils.chat_formatting import (
    box,
    escape,
    humanize_list,
    humanize_number,
    humanize_timedelta,
    inline,
    pagify,
)
from .commands.requires import PrivilegeLevel

_entities = {
    "*": "&midast;",
    "\\": "&bsol;",
    "`": "&grave;",
    "!": "&excl;",
    "{": "&lcub;",
    "[": "&lsqb;",
    "_": "&UnderBar;",
    "(": "&lpar;",
    "#": "&num;",
    ".": "&period;",
    "+": "&plus;",
    "}": "&rcub;",
    "]": "&rsqb;",
    ")": "&rpar;",
}

PRETTY_HTML_HEAD = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3rd Party Data Statements</title>
<style type="text/css">
body{margin:2em auto;max-width:800px;line-height:1.4;font-size:16px;
background-color=#EEEEEE;color:#454545;padding:1em;text-align:justify}
h1,h2,h3{line-height:1.2}
</style></head><body>
"""  # This ends up being a small bit extra that really makes a difference.

HTML_CLOSING = "</body></html>"


def entity_transformer(statement: str) -> str:
    return "".join(_entities.get(c, c) for c in statement)


if TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["Core"]

log = logging.getLogger("red")

_ = i18n.Translator("Core", __file__)

TokenConverter = commands.get_dict_converter(delims=[" ", ",", ";"])


class CoreLogic:
    def __init__(self, bot: "Red"):
        self.bot = bot
        self.bot.register_rpc_handler(self._load)
        self.bot.register_rpc_handler(self._unload)
        self.bot.register_rpc_handler(self._reload)
        self.bot.register_rpc_handler(self._name)
        self.bot.register_rpc_handler(self._prefixes)
        self.bot.register_rpc_handler(self._version_info)
        self.bot.register_rpc_handler(self._invite_url)

    async def _load(
        self, pkg_names: Iterable[str]
    ) -> Tuple[
        List[str], List[str], List[str], List[str], List[str], List[Tuple[str, str]], Set[str]
    ]:
        """
        Loads packages by name.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to load.

        Returns
        -------
        tuple
            7-tuple of:
              1. List of names of packages that loaded successfully
              2. List of names of packages that failed to load without specified reason
              3. List of names of packages that don't have a valid package name
              4. List of names of packages that weren't found in any cog path
              5. List of names of packages that are already loaded
              6. List of 2-tuples (pkg_name, reason) for packages
              that failed to load with a specified reason
              7. Set of repo names that use deprecated shared libraries
        """
        failed_packages = []
        loaded_packages = []
        invalid_pkg_names = []
        notfound_packages = []
        alreadyloaded_packages = []
        failed_with_reason_packages = []
        repos_with_shared_libs = set()

        bot = self.bot

        pkg_specs = []

        for name in pkg_names:
            if not name.isidentifier() or keyword.iskeyword(name):
                invalid_pkg_names.append(name)
                continue
            try:
                spec = await bot._cog_mgr.find_cog(name)
                if spec:
                    pkg_specs.append((spec, name))
                else:
                    notfound_packages.append(name)
            except Exception as e:
                log.exception("Package import failed", exc_info=e)

                exception_log = "Exception during import of package\n"
                exception_log += "".join(traceback.format_exception(type(e), e, e.__traceback__))
                bot._last_exception = exception_log
                failed_packages.append(name)

        async for spec, name in AsyncIter(pkg_specs, steps=10):
            try:
                self._cleanup_and_refresh_modules(spec.name)
                await bot.load_extension(spec)
            except errors.PackageAlreadyLoaded:
                alreadyloaded_packages.append(name)
            except errors.CogLoadError as e:
                failed_with_reason_packages.append((name, str(e)))
            except Exception as e:
                if isinstance(e, commands.CommandRegistrationError):
                    if e.alias_conflict:
                        error_message = _(
                            "Alias {alias_name} is already an existing command"
                            " or alias in one of the loaded cogs."
                        ).format(alias_name=inline(e.name))
                    else:
                        error_message = _(
                            "Command {command_name} is already an existing command"
                            " or alias in one of the loaded cogs."
                        ).format(command_name=inline(e.name))
                    failed_with_reason_packages.append((name, error_message))
                    continue

                log.exception("Package loading failed", exc_info=e)

                exception_log = "Exception during loading of package\n"
                exception_log += "".join(traceback.format_exception(type(e), e, e.__traceback__))
                bot._last_exception = exception_log
                failed_packages.append(name)
            else:
                await bot.add_loaded_package(name)
                loaded_packages.append(name)
                # remove in Red 3.4
                downloader = bot.get_cog("Downloader")
                if downloader is None:
                    continue
                try:
                    maybe_repo = await downloader._shared_lib_load_check(name)
                except Exception:
                    log.exception(
                        "Shared library check failed,"
                        " if you're not using modified Downloader, report this issue."
                    )
                    maybe_repo = None
                if maybe_repo is not None:
                    repos_with_shared_libs.add(maybe_repo.name)

        return (
            loaded_packages,
            failed_packages,
            invalid_pkg_names,
            notfound_packages,
            alreadyloaded_packages,
            failed_with_reason_packages,
            repos_with_shared_libs,
        )

    @staticmethod
    def _cleanup_and_refresh_modules(module_name: str) -> None:
        """Internally reloads modules so that changes are detected."""
        splitted = module_name.split(".")

        def maybe_reload(new_name):
            try:
                lib = sys.modules[new_name]
            except KeyError:
                pass
            else:
                importlib._bootstrap._exec(lib.__spec__, lib)

        # noinspection PyTypeChecker
        modules = itertools.accumulate(splitted, "{}.{}".format)
        for m in modules:
            maybe_reload(m)

        children = {name: lib for name, lib in sys.modules.items() if name.startswith(module_name)}
        for child_name, lib in children.items():
            importlib._bootstrap._exec(lib.__spec__, lib)

    async def _unload(self, pkg_names: Iterable[str]) -> Tuple[List[str], List[str]]:
        """
        Unloads packages with the given names.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to unload.

        Returns
        -------
        tuple
            2 element tuple of successful unloads and failed unloads.
        """
        failed_packages = []
        unloaded_packages = []

        bot = self.bot

        for name in pkg_names:
            if name in bot.extensions:
                bot.unload_extension(name)
                await bot.remove_loaded_package(name)
                unloaded_packages.append(name)
            else:
                failed_packages.append(name)

        return unloaded_packages, failed_packages

    async def _reload(
        self, pkg_names: Sequence[str]
    ) -> Tuple[
        List[str], List[str], List[str], List[str], List[str], List[Tuple[str, str]], Set[str]
    ]:
        """
        Reloads packages with the given names.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to reload.

        Returns
        -------
        tuple
            Tuple as returned by `CoreLogic._load()`
        """
        await self._unload(pkg_names)

        (
            loaded,
            load_failed,
            invalid_pkg_names,
            not_found,
            already_loaded,
            load_failed_with_reason,
            repos_with_shared_libs,
        ) = await self._load(pkg_names)

        return (
            loaded,
            load_failed,
            invalid_pkg_names,
            not_found,
            already_loaded,
            load_failed_with_reason,
            repos_with_shared_libs,
        )

    async def _name(self, name: Optional[str] = None) -> str:
        """
        Gets or sets the bot's username.

        Parameters
        ----------
        name : str
            If passed, the bot will change it's username.

        Returns
        -------
        str
            The current (or new) username of the bot.
        """
        if name is not None:
            await self.bot.user.edit(username=name)

        return self.bot.user.name

    async def _prefixes(self, prefixes: Optional[Sequence[str]] = None) -> List[str]:
        """
        Gets or sets the bot's global prefixes.

        Parameters
        ----------
        prefixes : list of str
            If passed, the bot will set it's global prefixes.

        Returns
        -------
        list of str
            The current (or new) list of prefixes.
        """
        if prefixes:
            await self.bot.set_prefixes(guild=None, prefixes=prefixes)
            return prefixes
        return await self.bot._prefix_cache.get_prefixes(guild=None)

    @classmethod
    async def _version_info(cls) -> Dict[str, str]:
        """
        Version information for Red and discord.py

        Returns
        -------
        dict
            `redbot` and `discordpy` keys containing version information for both.
        """
        return {"redbot": __version__, "discordpy": discord.__version__}

    async def _invite_url(self) -> str:
        """
        Generates the invite URL for the bot.

        Returns
        -------
        str
            Invite URL.
        """
        app_info = await self.bot.application_info()
        perms_int = await self.bot._config.invite_perm()
        permissions = discord.Permissions(perms_int)
        return discord.utils.oauth_url(app_info.id, permissions)

    @staticmethod
    async def _can_get_invite_url(ctx):
        is_owner = await ctx.bot.is_owner(ctx.author)
        is_invite_public = await ctx.bot._config.invite_public()
        return is_owner or is_invite_public


@i18n.cog_i18n(_)
class Core(commands.commands._RuleDropper, commands.Cog, CoreLogic):
    """
    The Core cog has many commands related to core functions.

    These commands come loaded with every Red bot, and cover some of the most basic usage of the bot.
    """

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete (Core Config is handled in a bot method ) """
        return

    @commands.command(hidden=True)
    async def ping(self, ctx: commands.Context):
        """Pong."""
        await ctx.send("Pong.")

    @commands.command()
    async def info(self, ctx: commands.Context):
        """Shows info about [botname].

        See `[p]set custominfo` to customize.
        """
        embed_links = await ctx.embed_requested()
        author_repo = "https://github.com/Twentysix26"
        org_repo = "https://github.com/Cog-Creators"
        red_repo = org_repo + "/Red-DiscordBot"
        red_pypi = "https://pypi.org/project/Red-DiscordBot"
        support_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days

        app_info = await self.bot.application_info()
        if app_info.team:
            owner = app_info.team.name
        else:
            owner = app_info.owner
        custom_info = await self.bot._config.custom_info()

        pypi_version, py_version_req = await fetch_latest_red_version_info()
        outdated = pypi_version and pypi_version > red_version_info

        if embed_links:
            dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
            python_version = "[{}.{}.{}]({})".format(*sys.version_info[:3], python_url)
            red_version = "[{}]({})".format(__version__, red_pypi)

            about = _(
                "This bot is an instance of [Red, an open source Discord bot]({}) "
                "created by [Twentysix]({}) and [improved by many]({}).\n\n"
                "Red is backed by a passionate community who contributes and "
                "creates content for everyone to enjoy. [Join us today]({}) "
                "and help us improve!\n\n"
                "(c) Cog Creators"
            ).format(red_repo, author_repo, org_repo, support_server_url)

            embed = discord.Embed(color=(await ctx.embed_colour()))
            embed.add_field(
                name=_("Instance owned by team") if app_info.team else _("Instance owned by"),
                value=str(owner),
            )
            embed.add_field(name="Python", value=python_version)
            embed.add_field(name="discord.py", value=dpy_version)
            embed.add_field(name=_("Red version"), value=red_version)
            if outdated in (True, None):
                if outdated is True:
                    outdated_value = _("Yes, {version} is available.").format(
                        version=str(pypi_version)
                    )
                else:
                    outdated_value = _("Checking for updates failed.")
                embed.add_field(name=_("Outdated"), value=outdated_value)
            if custom_info:
                embed.add_field(name=_("About this instance"), value=custom_info, inline=False)
            embed.add_field(name=_("About Red"), value=about, inline=False)

            embed.set_footer(
                text=_("Bringing joy since 02 Jan 2016 (over {} days ago!)").format(days_since)
            )
            await ctx.send(embed=embed)
        else:
            python_version = "{}.{}.{}".format(*sys.version_info[:3])
            dpy_version = "{}".format(discord.__version__)
            red_version = "{}".format(__version__)

            about = _(
                "This bot is an instance of Red, an open source Discord bot (1) "
                "created by Twentysix (2) and improved by many (3).\n\n"
                "Red is backed by a passionate community who contributes and "
                "creates content for everyone to enjoy. Join us today (4) "
                "and help us improve!\n\n"
                "(c) Cog Creators"
            )
            about = box(about)

            if app_info.team:
                extras = _(
                    "Instance owned by team: [{owner}]\n"
                    "Python:                 [{python_version}] (5)\n"
                    "discord.py:             [{dpy_version}] (6)\n"
                    "Red version:            [{red_version}] (7)\n"
                ).format(
                    owner=owner,
                    python_version=python_version,
                    dpy_version=dpy_version,
                    red_version=red_version,
                )
            else:
                extras = _(
                    "Instance owned by: [{owner}]\n"
                    "Python:            [{python_version}] (5)\n"
                    "discord.py:        [{dpy_version}] (6)\n"
                    "Red version:       [{red_version}] (7)\n"
                ).format(
                    owner=owner,
                    python_version=python_version,
                    dpy_version=dpy_version,
                    red_version=red_version,
                )

            if outdated in (True, None):
                if outdated is True:
                    outdated_value = _("Yes, {version} is available.").format(
                        version=str(pypi_version)
                    )
                else:
                    outdated_value = _("Checking for updates failed.")
                extras += _("Outdated:          [{state}]\n").format(state=outdated_value)

            red = (
                _("**About Red**\n")
                + about
                + "\n"
                + box(extras, lang="ini")
                + "\n"
                + _("Bringing joy since 02 Jan 2016 (over {} days ago!)").format(days_since)
                + "\n\n"
            )

            await ctx.send(red)
            if custom_info:
                custom_info = _("**About this instance**\n") + custom_info + "\n\n"
                await ctx.send(custom_info)
            refs = _(
                "**References**\n"
                "1. <{}>\n"
                "2. <{}>\n"
                "3. <{}>\n"
                "4. <{}>\n"
                "5. <{}>\n"
                "6. <{}>\n"
                "7. <{}>\n"
            ).format(
                red_repo, author_repo, org_repo, support_server_url, python_url, dpy_repo, red_pypi
            )
            await ctx.send(refs)

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows [botname]'s uptime."""
        since = ctx.bot.uptime.strftime("%Y-%m-%d %H:%M:%S")
        delta = datetime.datetime.utcnow() - self.bot.uptime
        uptime_str = humanize_timedelta(timedelta=delta) or _("Less than one second")
        await ctx.send(
            _("Been up for: **{time_quantity}** (since {timestamp} UTC)").format(
                time_quantity=uptime_str, timestamp=since
            )
        )

    @commands.group(cls=commands.commands._AlwaysAvailableGroup)
    async def mydata(self, ctx: commands.Context):
        """
        Commands which interact with the data [botname] has about you.

        More information can be found in the [End User Data Documentation.](https://docs.discord.red/en/stable/red_core_data_statement.html)
        """

    # 1/10 minutes. It's a static response, but the inability to lock
    # will annoy people if it's spammable
    @commands.cooldown(1, 600, commands.BucketType.user)
    @mydata.command(cls=commands.commands._AlwaysAvailableCommand, name="whatdata")
    async def mydata_whatdata(self, ctx: commands.Context):
        """
        Find out what type of data [botname] stores and why.

        **Example:**
            - `[p]mydata whatdata`
        """

        ver = "latest" if red_version_info.dev_release else "stable"
        link = f"https://docs.discord.red/en/{ver}/red_core_data_statement.html"
        await ctx.send(
            _(
                "This bot stores some data about users as necessary to function. "
                "This is mostly the ID your user is assigned by Discord, linked to "
                "a handful of things depending on what you interact with in the bot. "
                "There are a few commands which store it to keep track of who created "
                "something. (such as playlists) "
                "For full details about this as well as more in depth details of what "
                "is stored and why, see {link}.\n\n"
                "Additionally, 3rd party addons loaded by the bot's owner may or "
                "may not store additional things. "
                "You can use `{prefix}mydata 3rdparty` "
                "to view the statements provided by each 3rd-party addition."
            ).format(link=link, prefix=ctx.clean_prefix)
        )

    # 1/30 minutes. It's not likely to change much and uploads a standalone webpage.
    @commands.cooldown(1, 1800, commands.BucketType.user)
    @mydata.command(cls=commands.commands._AlwaysAvailableCommand, name="3rdparty")
    async def mydata_3rd_party(self, ctx: commands.Context):
        """View the End User Data statements of each 3rd-party module.

        This will send an attachment with the End User Data statements of all loaded 3rd party cogs.

        **Example:**
            - `[p]mydata 3rdparty`
        """

        # Can't check this as a command check, and want to prompt DMs as an option.
        if not ctx.channel.permissions_for(ctx.me).attach_files:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(_("I need to be able to attach files (try in DMs?)."))

        statements = {
            ext_name: getattr(ext, "__red_end_user_data_statement__", None)
            for ext_name, ext in ctx.bot.extensions.items()
            if not (ext.__package__ and ext.__package__.startswith("redbot."))
        }

        if not statements:
            return await ctx.send(
                _("This instance does not appear to have any 3rd-party extensions loaded.")
            )

        parts = []

        formatted_statements = []

        no_statements = []

        for ext_name, statement in sorted(statements.items()):
            if not statement:
                no_statements.append(ext_name)
            else:
                formatted_statements.append(
                    f"### {entity_transformer(ext_name)}\n\n{entity_transformer(statement)}"
                )

        if formatted_statements:
            parts.append(
                "## "
                + _("3rd party End User Data statements")
                + "\n\n"
                + _("The following are statements provided by 3rd-party extensions.")
            )
            parts.extend(formatted_statements)

        if no_statements:
            parts.append("## " + _("3rd-party extensions without statements\n"))
            for ext in no_statements:
                parts.append(f"\n - {entity_transformer(ext)}")

        generated = markdown.markdown("\n".join(parts), output_format="html")

        html = "\n".join((PRETTY_HTML_HEAD, generated, HTML_CLOSING))

        fp = io.BytesIO(html.encode())

        await ctx.send(
            _("Here's a generated page with the statements provided by 3rd-party extensions."),
            file=discord.File(fp, filename="3rd-party.html"),
        )

    async def get_serious_confirmation(self, ctx: commands.Context, prompt: str) -> bool:

        confirm_token = "".join(random.choices((*ascii_letters, *digits), k=8))

        await ctx.send(f"{prompt}\n\n{confirm_token}")
        try:
            message = await ctx.bot.wait_for(
                "message",
                check=lambda m: m.channel.id == ctx.channel.id and m.author.id == ctx.author.id,
                timeout=30,
            )
        except asyncio.TimeoutError:
            await ctx.send(_("Did not get confirmation, cancelling."))
        else:
            if message.content.strip() == confirm_token:
                return True
            else:
                await ctx.send(_("Did not get a matching confirmation, cancelling."))

        return False

    # 1 per day, not stored to config to avoid this being more stored data.
    # large bots shouldn't be restarting so often that this is an issue,
    # and small bots that do restart often don't have enough
    # users for this to be an issue.
    @commands.cooldown(1, 86400, commands.BucketType.user)
    @mydata.command(cls=commands.commands._ForgetMeSpecialCommand, name="forgetme")
    async def mydata_forgetme(self, ctx: commands.Context):
        """
        Have [botname] forget what it knows about you.

        This may not remove all data about you, data needed for operation,
        such as command cooldowns will be kept until no longer necessary.

        Further interactions with [botname] may cause it to learn about you again.

        **Example:**
            - `[p]mydata forgetme`
        """
        if ctx.assume_yes:
            # lol, no, we're not letting users schedule deletions every day to thrash the bot.
            ctx.command.reset_cooldown(ctx)  # We will however not let that lock them out either.
            return await ctx.send(
                _("This command ({command}) does not support non-interactive usage.").format(
                    command=ctx.command.qualified_name
                )
            )

        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of and/or disassociate "
                "data from you. It will not get rid of operational data such "
                "as modlog entries, warnings, or mutes. "
                "If you are sure this is what you want, "
                "please respond with the following:"
            ),
        ):
            ctx.command.reset_cooldown(ctx)
            return
        await ctx.send(_("This may take some time."))

        if await ctx.bot._config.datarequests.user_requests_are_strict():
            requester = "user_strict"
        else:
            requester = "user"

        results = await self.bot.handle_data_deletion_request(
            requester=requester, user_id=ctx.author.id
        )

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about you "
                    "(that I know how to delete) "
                    "{mention}, however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}.\n"
                    "Please contact the owner of this bot to address this.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    mention=ctx.author.mention,
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about you "
                    "(that I know how to delete) "
                    "{mention}, however the following cogs errored: {cogs}.\n"
                    "Please contact the owner of this bot to address this.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(mention=ctx.author.mention, cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about you "
                    "(that I know how to delete) "
                    "{mention}, however the following modules errored: {modules}.\n"
                    "Please contact the owner of this bot to address this.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(mention=ctx.author.mention, modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(
                _(
                    "I've deleted any non-operational data about you "
                    "(that I know how to delete) {mention}"
                ).format(mention=ctx.author.mention)
            )

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    # The cooldown of this should be longer once actually implemented
    # This is a couple hours, and lets people occasionally check status, I guess.
    @commands.cooldown(1, 7200, commands.BucketType.user)
    @mydata.command(cls=commands.commands._AlwaysAvailableCommand, name="getmydata")
    async def mydata_getdata(self, ctx: commands.Context):
        """[Coming Soon] Get what data [botname] has about you."""
        await ctx.send(
            _(
                "This command doesn't do anything yet, "
                "but we're working on adding support for this."
            )
        )

    @checks.is_owner()
    @mydata.group(name="ownermanagement")
    async def mydata_owner_management(self, ctx: commands.Context):
        """
        Commands for more complete data handling.
        """

    @mydata_owner_management.command(name="allowuserdeletions")
    async def mydata_owner_allow_user_deletions(self, ctx):
        """
        Set the bot to allow users to request a data deletion.

        This is on by default.
        Opposite of `[p]mydata ownermanagement disallowuserdeletions`

        **Example:**
            - `[p]mydata ownermanagement allowuserdeletions`
        """
        await ctx.bot._config.datarequests.allow_user_requests.set(True)
        await ctx.send(
            _(
                "User can delete their own data. "
                "This will not include operational data such as blocked users."
            )
        )

    @mydata_owner_management.command(name="disallowuserdeletions")
    async def mydata_owner_disallow_user_deletions(self, ctx):
        """
        Set the bot to not allow users to request a data deletion.

        Opposite of `[p]mydata ownermanagement allowuserdeletions`

        **Example:**
            - `[p]mydata ownermanagement disallowuserdeletions`
        """
        await ctx.bot._config.datarequests.allow_user_requests.set(False)
        await ctx.send(_("User can not delete their own data."))

    @mydata_owner_management.command(name="setuserdeletionlevel")
    async def mydata_owner_user_deletion_level(self, ctx, level: int):
        """
        Sets how user deletions are treated.

        **Example:**
            - `[p]mydata ownermanagement setuserdeletionlevel 1`

        **Arguments:**
            - `<level>` - The strictness level for user deletion. See Level guide below.

        Level:
            - `0`: What users can delete is left entirely up to each cog.
            - `1`: Cogs should delete anything the cog doesn't need about the user.
        """

        if level == 1:
            await ctx.bot._config.datarequests.user_requests_are_strict.set(True)
            await ctx.send(
                _(
                    "Cogs will be instructed to remove all non operational "
                    "data upon a user request."
                )
            )
        elif level == 0:
            await ctx.bot._config.datarequests.user_requests_are_strict.set(False)
            await ctx.send(
                _(
                    "Cogs will be informed a user has made a data deletion request, "
                    "and the details of what to delete will be left to the "
                    "discretion of the cog author."
                )
            )
        else:
            await ctx.send_help()

    @mydata_owner_management.command(name="processdiscordrequest")
    async def mydata_discord_deletion_request(self, ctx, user_id: int):
        """
        Handle a deletion request from Discord.

        This will cause the bot to get rid of or disassociate all data from the specified user ID.
        You should not use this unless Discord has specifically requested this with regard to a deleted user.
        This will remove the user from various anti-abuse measures.
        If you are processing a manual request from a user, you may want `[p]mydata ownermanagement deleteforuser` instead.

        **Arguments:**
            - `<user_id>` - The id of the user whose data would be deleted.
        """

        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of or disassociate all data "
                "from the specified user ID. You should not use this unless "
                "Discord has specifically requested this with regard to a deleted user. "
                "This will remove the user from various anti-abuse measures. "
                "If you are processing a manual request from a user, you may want "
                "`{prefix}{command_name}` instead."
                "\n\nIf you are sure this is what you intend to do "
                "please respond with the following:"
            ).format(prefix=ctx.clean_prefix, command_name="mydata ownermanagement deleteforuser"),
        ):
            return
        results = await self.bot.handle_data_deletion_request(
            requester="discord_deleted_user", user_id=user_id
        )

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following cogs errored: {cogs}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(_("I've deleted all data about that user that I know how to delete."))

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    @mydata_owner_management.command(name="deleteforuser")
    async def mydata_user_deletion_request_by_owner(self, ctx, user_id: int):
        """Delete data [botname] has about a user for a user.

        This will cause the bot to get rid of or disassociate a lot of non-operational data from the specified user.
        Users have access to a different command for this unless they can't interact with the bot at all.
        This is a mostly safe operation, but you should not use it unless processing a request from this user as it may impact their usage of the bot.

        **Arguments:**
            - `<user_id>` - The id of the user whose data would be deleted.
        """
        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of or disassociate "
                "a lot of non-operational data from the "
                "specified user. Users have access to "
                "different command for this unless they can't interact with the bot at all. "
                "This is a mostly safe operation, but you should not use it "
                "unless processing a request from this "
                "user as it may impact their usage of the bot. "
                "\n\nIf you are sure this is what you intend to do "
                "please respond with the following:"
            ),
        ):
            return

        if await ctx.bot._config.datarequests.user_requests_are_strict():
            requester = "user_strict"
        else:
            requester = "user"

        results = await self.bot.handle_data_deletion_request(requester=requester, user_id=user_id)

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about that user, "
                    "(that I know how to delete) "
                    "however the following cogs errored: {cogs}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all non-operational data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(
                _(
                    "I've deleted all non-operational data about that user "
                    "that I know how to delete."
                )
            )

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    @mydata_owner_management.command(name="deleteuserasowner")
    async def mydata_user_deletion_by_owner(self, ctx, user_id: int):
        """Delete data [botname] has about a user.

        This will cause the bot to get rid of or disassociate a lot of data about the specified user.
        This may include more than just end user data, including anti abuse records.

        **Arguments:**
            - `<user_id>` - The id of the user whose data would be deleted.
        """
        if not await self.get_serious_confirmation(
            ctx,
            _(
                "This will cause the bot to get rid of or disassociate "
                "a lot of data about the specified user. "
                "This may include more than just end user data, including "
                "anti abuse records."
                "\n\nIf you are sure this is what you intend to do "
                "please respond with the following:"
            ),
        ):
            return
        results = await self.bot.handle_data_deletion_request(requester="owner", user_id=user_id)

        if results.failed_cogs and results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}. "
                    "Additionally, the following cogs errored: {cogs}\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(
                    cogs=humanize_list(results.failed_cogs),
                    modules=humanize_list(results.failed_modules),
                )
            )
        elif results.failed_cogs:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following cogs errored: {cogs}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(cogs=humanize_list(results.failed_cogs))
            )
        elif results.failed_modules:
            await ctx.send(
                _(
                    "I tried to delete all data about that user, "
                    "(that I know how to delete) "
                    "however the following modules errored: {modules}.\n"
                    "Please check your logs and contact the creators of "
                    "these cogs and modules.\n"
                    "Note: Outside of these failures, data should have been deleted."
                ).format(modules=humanize_list(results.failed_modules))
            )
        else:
            await ctx.send(_("I've deleted all data about that user that I know how to delete."))

        if results.unhandled:
            await ctx.send(
                _("{mention} The following cogs did not handle deletion:\n{cogs}.").format(
                    mention=ctx.author.mention, cogs=humanize_list(results.unhandled)
                )
            )

    @commands.group()
    async def embedset(self, ctx: commands.Context):
        """
        Commands for toggling embeds on or off.

        This setting determines whether or not to use embeds as a response to a command (for commands that support it).
        The default is to use embeds.

        The embed settings are checked until the first True/False in this order:
            - In guild context:
                1. Channel override - `[p]embedset channel`
                2. Server command override - `[p]embedset command server`
                3. Server override - `[p]embedset server`
                4. Global command override - `[p]embedset command global`
                5. Global setting  -`[p]embedset global`

            - In DM context:
                1. User override - `[p]embedset user`
                2. Global command override - `[p]embedset command global`
                3. Global setting - `[p]embedset global`
        """

    @embedset.command(name="showsettings")
    async def embedset_showsettings(self, ctx: commands.Context, command_name: str = None) -> None:
        """
        Show the current embed settings.

        Provide a command name to check for command specific embed settings.

        **Examples:**
            - `[p]embedset showsettings` - Shows embed settings.
            - `[p]embedset showsettings info` - Also shows embed settings for the 'info' command.
            - `[p]embedset showsettings "ignore list"` - Checking subcommands requires quotes.

        **Arguments:**
            - `[command_name]` - Checks this command for command specific embed settings.
        """
        if command_name is not None:
            command_obj: Optional[commands.Command] = ctx.bot.get_command(command_name)
            if command_obj is None:
                await ctx.send(
                    _("I couldn't find that command. Please note that it is case sensitive.")
                )
                return
            # qualified name might be different if alias was passed to this command
            command_name = command_obj.qualified_name

        text = _("Embed settings:\n\n")
        global_default = await self.bot._config.embeds()
        text += _("Global default: {value}\n").format(value=global_default)

        if command_name is not None:
            scope = self.bot._config.custom("COMMAND", command_name, 0)
            global_command_setting = await scope.embeds()
            text += _("Global command setting for {command} command: {value}\n").format(
                command=inline(command_name), value=global_command_setting
            )

        if ctx.guild:
            guild_setting = await self.bot._config.guild(ctx.guild).embeds()
            text += _("Guild setting: {value}\n").format(value=guild_setting)

            if command_name is not None:
                scope = self.bot._config.custom("COMMAND", command_name, ctx.guild.id)
                command_setting = await scope.embeds()
                text += _("Server command setting for {command} command: {value}\n").format(
                    command=inline(command_name), value=command_setting
                )

        if ctx.channel:
            channel_setting = await self.bot._config.channel(ctx.channel).embeds()
            text += _("Channel setting: {value}\n").format(value=channel_setting)

        user_setting = await self.bot._config.user(ctx.author).embeds()
        text += _("User setting: {value}").format(value=user_setting)
        await ctx.send(box(text))

    @embedset.command(name="global")
    @checks.is_owner()
    async def embedset_global(self, ctx: commands.Context):
        """
        Toggle the global embed setting.

        This is used as a fallback if the user or guild hasn't set a preference.
        The default is to use embeds.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Example:**
            - `[p]embedset global`
        """
        current = await self.bot._config.embeds()
        if current:
            await self.bot._config.embeds.set(False)
            await ctx.send(_("Embeds are now disabled by default."))
        else:
            await self.bot._config.embeds.clear()
            await ctx.send(_("Embeds are now enabled by default."))

    @embedset.command(name="server", aliases=["guild"])
    @checks.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    async def embedset_guild(self, ctx: commands.Context, enabled: bool = None):
        """
        Set the server's embed setting.

        If set, this is used instead of the global default to determine whether or not to use embeds.
        This is used for all commands done in a server.

        If enabled is left blank, the setting will be unset and the global default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
            - `[p]embedset server False` - Disables embeds on this server.
            - `[p]embedset server` - Resets value to use global default.

        **Arguments:**
            - `[enabled]` - Whether to use embeds on this server. Leave blank to reset to default.
        """
        if enabled is None:
            await self.bot._config.guild(ctx.guild).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))
            return

        await self.bot._config.guild(ctx.guild).embeds.set(enabled)
        await ctx.send(
            _("Embeds are now enabled for this guild.")
            if enabled
            else _("Embeds are now disabled for this guild.")
        )

    @checks.guildowner_or_permissions(administrator=True)
    @embedset.group(name="command", invoke_without_command=True)
    async def embedset_command(
        self, ctx: commands.Context, command_name: str, enabled: bool = None
    ) -> None:
        """
        Sets a command's embed setting.

        If you're the bot owner, this will try to change the command's embed setting globally by default.
        Otherwise, this will try to change embed settings on the current server.

        If enabled is left blank, the setting will be unset.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
            - `[p]embedset command info` - Clears command specific embed settings for 'info'.
            - `[p]embedset command info False` - Disables embeds for 'info'.
            - `[p]embedset command "ignore list" True` - Quotes are needed for subcommands.

        **Arguments:**
            - `[enabled]` - Whether to use embeds for this command. Leave blank to reset to default.
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await self.embedset_command_global(ctx, command_name, enabled)
        else:
            await self.embedset_command_guild(ctx, command_name, enabled)

    def _check_if_command_requires_embed_links(self, command_obj: commands.Command) -> None:
        for command in itertools.chain((command_obj,), command_obj.parents):
            if command_obj.requires.bot_perms.embed_links:
                # a slight abuse of this exception to save myself two lines later...
                raise commands.UserFeedbackCheckFailure(
                    _(
                        "The passed command requires Embed Links permission"
                        " and therefore cannot be set to not use embeds."
                    )
                )

    @commands.is_owner()
    @embedset_command.command(name="global")
    async def embedset_command_global(
        self, ctx: commands.Context, command_name: str, enabled: bool = None
    ):
        """
        Sets a command's embed setting globally.

        If set, this is used instead of the global default to determine whether or not to use embeds.

        If enabled is left blank, the setting will be unset.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
            - `[p]embedset command global info` - Clears command specific embed settings for 'info'.
            - `[p]embedset command global info False` - Disables embeds for 'info'.
            - `[p]embedset command global "ignore list" True` - Quotes are needed for subcommands.

        **Arguments:**
            - `[enabled]` - Whether to use embeds for this command. Leave blank to reset to default.
        """
        command_obj: Optional[commands.Command] = ctx.bot.get_command(command_name)
        if command_obj is None:
            await ctx.send(
                _("I couldn't find that command. Please note that it is case sensitive.")
            )
            return
        self._check_if_command_requires_embed_links(command_obj)
        # qualified name might be different if alias was passed to this command
        command_name = command_obj.qualified_name

        if enabled is None:
            await self.bot._config.custom("COMMAND", command_name, 0).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))
            return

        await self.bot._config.custom("COMMAND", command_name, 0).embeds.set(enabled)
        if enabled:
            await ctx.send(
                _("Embeds are now enabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )
        else:
            await ctx.send(
                _("Embeds are now disabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )

    @commands.guild_only()
    @embedset_command.command(name="server", aliases=["guild"])
    async def embedset_command_guild(
        self, ctx: commands.GuildContext, command_name: str, enabled: bool = None
    ):
        """
        Sets a commmand's embed setting for the current server.

        If set, this is used instead of the server default to determine whether or not to use embeds.

        If enabled is left blank, the setting will be unset and the server default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
            - `[p]embedset command server info` - Clears command specific embed settings for 'info'.
            - `[p]embedset command server info False` - Disables embeds for 'info'.
            - `[p]embedset command server "ignore list" True` - Quotes are needed for subcommands.

        **Arguments:**
            - `[enabled]` - Whether to use embeds for this command. Leave blank to reset to default.
        """
        command_obj: Optional[commands.Command] = ctx.bot.get_command(command_name)
        if command_obj is None:
            await ctx.send(
                _("I couldn't find that command. Please note that it is case sensitive.")
            )
            return
        self._check_if_command_requires_embed_links(command_obj)
        # qualified name might be different if alias was passed to this command
        command_name = command_obj.qualified_name

        if enabled is None:
            await self.bot._config.custom("COMMAND", command_name, ctx.guild.id).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the server setting."))
            return

        await self.bot._config.custom("COMMAND", command_name, ctx.guild.id).embeds.set(enabled)
        if enabled:
            await ctx.send(
                _("Embeds are now enabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )
        else:
            await ctx.send(
                _("Embeds are now disabled for {command_name} command.").format(
                    command_name=inline(command_name)
                )
            )

    @embedset.command(name="channel")
    @checks.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    async def embedset_channel(self, ctx: commands.Context, enabled: bool = None):
        """
        Set's a channel's embed setting.

        If set, this is used instead of the guild and command defaults to determine whether or not to use embeds.
        This is used for all commands done in a channel.

        If enabled is left blank, the setting will be unset and the guild default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
            - `[p]embedset channel False` - Disables embeds in this channel.
            - `[p]embedset channel` - Resets value to use guild default.

        **Arguments:**
            - `[enabled]` - Whether to use embeds in this channel. Leave blank to reset to default.
        """
        if enabled is None:
            await self.bot._config.channel(ctx.channel).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))
            return

        await self.bot._config.channel(ctx.channel).embeds.set(enabled)
        await ctx.send(
            _("Embeds are now {} for this channel.").format(
                _("enabled") if enabled else _("disabled")
            )
        )

    @embedset.command(name="user")
    async def embedset_user(self, ctx: commands.Context, enabled: bool = None):
        """
        Sets personal embed setting for DMs.

        If set, this is used instead of the global default to determine whether or not to use embeds.
        This is used for all commands executed in a DM with the bot.

        If enabled is left blank, the setting will be unset and the global default will be used instead.

        To see full evaluation order of embed settings, run `[p]help embedset`.

        **Examples:**
            - `[p]embedset user False` - Disables embeds in your DMs.
            - `[p]embedset user` - Resets value to use global default.

        **Arguments:**
            - `[enabled]` - Whether to use embeds in your DMs. Leave blank to reset to default.
        """
        if enabled is None:
            await self.bot._config.user(ctx.author).embeds.clear()
            await ctx.send(_("Embeds will now fall back to the global setting."))

        await self.bot._config.user(ctx.author).embeds.set(enabled)
        await ctx.send(
            _("Embeds are now enabled for you in DMs.")
            if enabled
            else _("Embeds are now disabled for you in DMs.")
        )

    @commands.command()
    @checks.is_owner()
    async def traceback(self, ctx: commands.Context, public: bool = False):
        """Sends to the owner the last command exception that has occurred.

        If public (yes is specified), it will be sent to the chat instead.

        Warning: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.

        **Examples:**
            - `[p]traceback` - Sends the traceback to your DMs.
            - `[p]traceback True` - Sends the last traceback in the current context.

        **Arguments:**
            - `[public]` - Whether to send the traceback to the current context. Leave blank to send to your DMs.
        """
        if not public:
            destination = ctx.author
        else:
            destination = ctx.channel

        if self.bot._last_exception:
            for page in pagify(self.bot._last_exception, shorten_by=10):
                try:
                    await destination.send(box(page, lang="py"))
                except discord.HTTPException:
                    await ctx.channel.send(
                        "I couldn't send the traceback message to you in DM. "
                        "Either you blocked me or you disabled DMs in this server."
                    )
                    return
        else:
            await ctx.send(_("No exception has occurred yet."))

    @commands.command()
    @commands.check(CoreLogic._can_get_invite_url)
    async def invite(self, ctx):
        """Shows [botname]'s invite url.

        This will always send the invite to DMs to keep it private.

        This command is locked to the owner unless `[p]inviteset public` is set to True.

        **Example:**
            - `[p]invite`
        """
        try:
            await ctx.author.send(await self._invite_url())
        except discord.errors.Forbidden:
            await ctx.send(
                "I couldn't send the invite message to you in DM. "
                "Either you blocked me or you disabled DMs in this server."
            )

    @commands.group()
    @checks.is_owner()
    async def inviteset(self, ctx):
        """Commands to setup [botname]'s invite settings."""
        pass

    @inviteset.command()
    async def public(self, ctx, confirm: bool = False):
        """
        Toggles if `[p]invite` should be accessible for the average user.

        The bot must be made into a `Public bot` in the developer dashboard for public invites to work.

        **Example:**
            - `[p]inviteset public yes` - Toggles the public invite setting.

        **Arguments:**
            - `[confirm]` - Required to set to public. Not required to toggle back to private.
        """
        if await self.bot._config.invite_public():
            await self.bot._config.invite_public.set(False)
            await ctx.send("The invite is now private.")
            return
        app_info = await self.bot.application_info()
        if not app_info.bot_public:
            await ctx.send(
                "I am not a public bot. That means that nobody except "
                "you can invite me on new servers.\n\n"
                "You can change this by ticking `Public bot` in "
                "your token settings: "
                "https://discord.com/developers/applications/{0}/bot".format(self.bot.user.id)
            )
            return
        if not confirm:
            await ctx.send(
                "You're about to make the `{0}invite` command public. "
                "All users will be able to invite me on their server.\n\n"
                "If you agree, you can type `{0}inviteset public yes`.".format(ctx.clean_prefix)
            )
        else:
            await self.bot._config.invite_public.set(True)
            await ctx.send("The invite command is now public.")

    @inviteset.command()
    async def perms(self, ctx, level: int):
        """
        Make the bot create its own role with permissions on join.

        The bot will create its own role with the desired permissions when it joins a new server. This is a special role that can't be deleted or removed from the bot.

        For that, you need to provide a valid permissions level.
        You can generate one here: https://discordapi.com/permissions.html

        Please note that you might need two factor authentication for some permissions.

        **Example:**
            - `[p]inviteset perms 134217728` - Adds a "Manage Nicknames" permission requirement to the invite.

        **Arguments:**
            - `<level>` - The permission level to require for the bot in the generated invite.
        """
        await self.bot._config.invite_perm.set(level)
        await ctx.send("The new permissions level has been set.")

    @commands.command()
    @checks.is_owner()
    async def leave(self, ctx: commands.Context, *servers: GuildConverter):
        """
        Leaves servers.

        If no server IDs are passed the local server will be left instead.

        Note: This command is interactive.

        **Examples:**
            - `[p]leave` - Leave the current server.
            - `[p]leave "Red - Discord Bot"` - Quotes are necessary when there are spaces in the name.
            - `[p]leave 133049272517001216 240154543684321280` - Leaves multiple servers, using IDs.

        **Arguments:**
            - `[servers...]` - The servers to leave. When blank, attempts to leave the current server.
        """
        guilds = servers
        if ctx.guild is None and not guilds:
            return await ctx.send(_("You need to specify at least one server ID."))

        leaving_local_guild = not guilds

        if leaving_local_guild:
            guilds = (ctx.guild,)
            msg = (
                _("You haven't passed any server ID. Do you want me to leave this server?")
                + " (y/n)"
            )
        else:
            msg = (
                _("Are you sure you want me to leave these servers?")
                + " (y/n):\n"
                + "\n".join(f"- {guild.name} (`{guild.id}`)" for guild in guilds)
            )

        for guild in guilds:
            if guild.owner.id == ctx.me.id:
                return await ctx.send(
                    _("I cannot leave the server `{server_name}`: I am the owner of it.").format(
                        server_name=guild.name
                    )
                )

        for page in pagify(msg):
            await ctx.send(page)
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return
        else:
            if pred.result is True:
                if leaving_local_guild is True:
                    await ctx.send(_("Alright. Bye :wave:"))
                else:
                    await ctx.send(
                        _("Alright. Leaving {number} servers...").format(number=len(guilds))
                    )
                for guild in guilds:
                    log.debug("Leaving guild '%s' (%s)", guild.name, guild.id)
                    await guild.leave()
            else:
                if leaving_local_guild is True:
                    await ctx.send(_("Alright, I'll stay then. :)"))
                else:
                    await ctx.send(_("Alright, I'm not leaving those servers."))

    @commands.command()
    @checks.is_owner()
    async def servers(self, ctx: commands.Context):
        """
        Lists the servers [botname] is currently in.

        Note: This command is interactive.
        """
        guilds = sorted(self.bot.guilds, key=lambda s: s.name.lower())
        msg = "\n".join(f"{guild.name} (`{guild.id}`)\n" for guild in guilds)

        pages = list(pagify(msg, ["\n"], page_length=1000))

        if len(pages) == 1:
            await ctx.send(pages[0])
        else:
            await menu(ctx, pages, DEFAULT_CONTROLS)

    @commands.command(require_var_positional=True)
    @checks.is_owner()
    async def load(self, ctx: commands.Context, *cogs: str):
        """Loads cog packages from the local paths and installed cogs.

        See packages available to load with `[p]cogs`.

        Additional cogs can be added using Downloader, or from local paths using `[p]addpath`.

        **Examples:**
            - `[p]load general` - Loads the `general` cog.
            - `[p]load admin mod mutes` - Loads multiple cogs.

        **Arguments:**
            - `<cogs...>` - The cog packages to load.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            (
                loaded,
                failed,
                invalid_pkg_names,
                not_found,
                already_loaded,
                failed_with_reason,
                repos_with_shared_libs,
            ) = await self._load(cogs)

        output = []

        if loaded:
            loaded_packages = humanize_list([inline(package) for package in loaded])
            formed = _("Loaded {packs}.").format(packs=loaded_packages)
            output.append(formed)

        if already_loaded:
            if len(already_loaded) == 1:
                formed = _("The following package is already loaded: {pack}").format(
                    pack=inline(already_loaded[0])
                )
            else:
                formed = _("The following packages are already loaded: {packs}").format(
                    packs=humanize_list([inline(package) for package in already_loaded])
                )
            output.append(formed)

        if failed:
            if len(failed) == 1:
                formed = _(
                    "Failed to load the following package: {pack}."
                    "\nCheck your console or logs for details."
                ).format(pack=inline(failed[0]))
            else:
                formed = _(
                    "Failed to load the following packages: {packs}"
                    "\nCheck your console or logs for details."
                ).format(packs=humanize_list([inline(package) for package in failed]))
            output.append(formed)

        if invalid_pkg_names:
            if len(invalid_pkg_names) == 1:
                formed = _(
                    "The following name is not a valid package name: {pack}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(pack=inline(invalid_pkg_names[0]))
            else:
                formed = _(
                    "The following names are not valid package names: {packs}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(packs=humanize_list([inline(package) for package in invalid_pkg_names]))
            output.append(formed)

        if not_found:
            if len(not_found) == 1:
                formed = _("The following package was not found in any cog path: {pack}.").format(
                    pack=inline(not_found[0])
                )
            else:
                formed = _(
                    "The following packages were not found in any cog path: {packs}"
                ).format(packs=humanize_list([inline(package) for package in not_found]))
            output.append(formed)

        if failed_with_reason:
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason])
            if len(failed_with_reason) == 1:
                formed = _(
                    "This package could not be loaded for the following reason:\n\n{reason}"
                ).format(reason=reasons)
            else:
                formed = _(
                    "These packages could not be loaded for the following reasons:\n\n{reasons}"
                ).format(reasons=reasons)
            output.append(formed)

        if repos_with_shared_libs:
            if len(repos_with_shared_libs) == 1:
                formed = _(
                    "**WARNING**: The following repo is using shared libs"
                    " which are marked for removal in the future: {repo}.\n"
                    "You should inform maintainer of the repo about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in the future: {repos}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repos=humanize_list([inline(repo) for repo in repos_with_shared_libs]))
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(
                total_message, delims=["\n", ", "], priority=True, page_length=1500
            ):
                if page.startswith(", "):
                    page = page[2:]
                await ctx.send(page)

    @commands.command(require_var_positional=True)
    @checks.is_owner()
    async def unload(self, ctx: commands.Context, *cogs: str):
        """Unloads previously loaded cog packages.

        See packages available to unload with `[p]cogs`.

        **Examples:**
            - `[p]unload general` - Unloads the `general` cog.
            - `[p]unload admin mod mutes` - Unloads multiple cogs.

        **Arguments:**
            - `<cogs...>` - The cog packages to unload.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        unloaded, failed = await self._unload(cogs)

        output = []

        if unloaded:
            if len(unloaded) == 1:
                formed = _("The following package was unloaded: {pack}.").format(
                    pack=inline(unloaded[0])
                )
            else:
                formed = _("The following packages were unloaded: {packs}.").format(
                    packs=humanize_list([inline(package) for package in unloaded])
                )
            output.append(formed)

        if failed:
            if len(failed) == 1:
                formed = _("The following package was not loaded: {pack}.").format(
                    pack=inline(failed[0])
                )
            else:
                formed = _("The following packages were not loaded: {packs}.").format(
                    packs=humanize_list([inline(package) for package in failed])
                )
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(total_message):
                await ctx.send(page)

    @commands.command(require_var_positional=True)
    @checks.is_owner()
    async def reload(self, ctx: commands.Context, *cogs: str):
        """Reloads cog packages.

        This will unload and then load the specified cogs.

        Cogs that were not loaded will only be loaded.

        **Examples:**
            - `[p]reload general` - Unloads then loads the `general` cog.
            - `[p]reload admin mod mutes` - Unloads then loads multiple cogs.

        **Arguments:**
            - `<cogs...>` - The cog packages to reload.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            (
                loaded,
                failed,
                invalid_pkg_names,
                not_found,
                already_loaded,
                failed_with_reason,
                repos_with_shared_libs,
            ) = await self._reload(cogs)

        output = []

        if loaded:
            loaded_packages = humanize_list([inline(package) for package in loaded])
            formed = _("Reloaded {packs}.").format(packs=loaded_packages)
            output.append(formed)

        if failed:
            if len(failed) == 1:
                formed = _(
                    "Failed to reload the following package: {pack}."
                    "\nCheck your console or logs for details."
                ).format(pack=inline(failed[0]))
            else:
                formed = _(
                    "Failed to reload the following packages: {packs}"
                    "\nCheck your console or logs for details."
                ).format(packs=humanize_list([inline(package) for package in failed]))
            output.append(formed)

        if invalid_pkg_names:
            if len(invalid_pkg_names) == 1:
                formed = _(
                    "The following name is not a valid package name: {pack}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(pack=inline(invalid_pkg_names[0]))
            else:
                formed = _(
                    "The following names are not valid package names: {packs}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(packs=humanize_list([inline(package) for package in invalid_pkg_names]))
            output.append(formed)

        if not_found:
            if len(not_found) == 1:
                formed = _("The following package was not found in any cog path: {pack}.").format(
                    pack=inline(not_found[0])
                )
            else:
                formed = _(
                    "The following packages were not found in any cog path: {packs}"
                ).format(packs=humanize_list([inline(package) for package in not_found]))
            output.append(formed)

        if failed_with_reason:
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason])
            if len(failed_with_reason) == 1:
                formed = _(
                    "This package could not be reloaded for the following reason:\n\n{reason}"
                ).format(reason=reasons)
            else:
                formed = _(
                    "These packages could not be reloaded for the following reasons:\n\n{reasons}"
                ).format(reasons=reasons)
            output.append(formed)

        if repos_with_shared_libs:
            if len(repos_with_shared_libs) == 1:
                formed = _(
                    "**WARNING**: The following repo is using shared libs"
                    " which are marked for removal in the future: {repo}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in the future: {repos}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repos=humanize_list([inline(repo) for repo in repos_with_shared_libs]))
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(total_message):
                await ctx.send(page)

    @commands.command(name="shutdown")
    @checks.is_owner()
    async def _shutdown(self, ctx: commands.Context, silently: bool = False):
        """Shuts down the bot.

        Allows [botname] to shut down gracefully.

        This is the recommended method for shutting down the bot.

        **Examples:**
            - `[p]shutdown`
            - `[p]shutdown True` - Shutdowns silently.

        **Arguments:**
            - `[silently]` - Whether to skip sending the shutdown message. Defaults to False.
        """
        wave = "\N{WAVING HAND SIGN}"
        skin = "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Shutting down... ") + wave + skin)
        await ctx.bot.shutdown()

    @commands.command(name="restart")
    @checks.is_owner()
    async def _restart(self, ctx: commands.Context, silently: bool = False):
        """Attempts to restart [botname].

        Makes [botname] quit with exit code 26.
        The restart is not guaranteed: it must be dealt with by the process manager in use.

        **Examples:**
            - `[p]restart`
            - `[p]restart True` - Restarts silently.

        **Arguments:**
            - `[silently]` - Whether to skip sending the restart message. Defaults to False.
        """
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Restarting..."))
        await ctx.bot.shutdown(restart=True)

    @commands.group(name="set")
    async def _set(self, ctx: commands.Context):
        """Commands for changing [botname]'s settings."""

    @_set.command("showsettings")
    async def set_showsettings(self, ctx: commands.Context):
        """
        Show the current settings for [botname].
        """
        if ctx.guild:
            guild_data = await ctx.bot._config.guild(ctx.guild).all()
            guild = ctx.guild
            admin_role_ids = guild_data["admin_role"]
            admin_role_names = [r.name for r in guild.roles if r.id in admin_role_ids]
            admin_roles_str = humanize_list(admin_role_names) if admin_role_names else "Not Set."
            mod_role_ids = guild_data["mod_role"]
            mod_role_names = [r.name for r in guild.roles if r.id in mod_role_ids]
            mod_roles_str = humanize_list(mod_role_names) if mod_role_names else "Not Set."

            guild_locale = await i18n.get_locale_from_guild(self.bot, ctx.guild)
            guild_regional_format = (
                await i18n.get_regional_format_from_guild(self.bot, ctx.guild) or guild_locale
            )

            guild_settings = _(
                "Admin roles: {admin}\n"
                "Mod roles: {mod}\n"
                "Locale: {guild_locale}\n"
                "Regional format: {guild_regional_format}\n"
            ).format(
                admin=admin_roles_str,
                mod=mod_roles_str,
                guild_locale=guild_locale,
                guild_regional_format=guild_regional_format,
            )
        else:
            guild_settings = ""

        prefixes = await ctx.bot._prefix_cache.get_prefixes(ctx.guild)
        global_data = await ctx.bot._config.all()
        locale = global_data["locale"]
        regional_format = global_data["regional_format"] or locale
        colour = discord.Colour(global_data["color"])
        sudotime = (
            _("SU Timeout: {delay}\n").format(
                delay=humanize_timedelta(seconds=global_data["sudotime"])
            )
            if ctx.bot._sudo_ctx_var is not None
            else ""
        )

        prefix_string = " ".join(prefixes)
        settings = _(
            "{bot_name} Settings:\n\n"
            "Prefixes: {prefixes}\n"
            "{guild_settings}"
            "Global locale: {locale}\n"
            "Global regional format: {regional_format}\n"
            "Default embed colour: {colour}\n"
            "{sudotime}"
        ).format(
            bot_name=ctx.bot.user.name,
            prefixes=prefix_string,
            guild_settings=guild_settings,
            locale=locale,
            regional_format=regional_format,
            colour=colour,
            sudotime=sudotime,
        )
        for page in pagify(settings):
            await ctx.send(box(page))

    @checks.guildowner_or_permissions(administrator=True)
    @_set.command(name="deletedelay")
    @commands.guild_only()
    async def deletedelay(self, ctx: commands.Context, time: int = None):
        """Set the delay until the bot removes the command message.

        Must be between -1 and 60.

        Set to -1 to disable this feature.

        This is only applied to the current server and not globally.

        **Examples:**
            - `[p]set deletedelay` - Shows the current delete delay setting.
            - `[p]set deletedelay 60` - Sets the delete delay to the max of 60 seconds.
            - `[p]set deletedelay -1` - Disables deleting command messages.

        **Arguments:**
            - `[time]` - The seconds to wait before deleting the command message. Use -1 to disable.
        """
        guild = ctx.guild
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            await ctx.bot._config.guild(guild).delete_delay.set(time)
            if time == -1:
                await ctx.send(_("Command deleting disabled."))
            else:
                await ctx.send(_("Delete delay set to {num} seconds.").format(num=time))
        else:
            delay = await ctx.bot._config.guild(guild).delete_delay()
            if delay != -1:
                await ctx.send(
                    _(
                        "Bot will delete command messages after"
                        " {num} seconds. Set this value to -1 to"
                        " stop deleting messages"
                    ).format(num=delay)
                )
            else:
                await ctx.send(_("I will not delete command messages."))

    @checks.is_owner()
    @_set.command(name="description")
    async def setdescription(self, ctx: commands.Context, *, description: str = ""):
        """
        Sets the bot's description.

        Use without a description to reset.
        This is shown in a few locations, including the help menu.

        The maximum description length is 250 characters to ensure it displays properly.

        The default is "Red V3".

        **Examples:**
            - `[p]set description` - Resets the description to the default setting.
            - `[p]set description MyBot: A Red V3 Bot`

        **Arguments:**
            - `[description]` - The description to use for this bot. Leave blank to reset to the default.
        """
        if not description:
            await ctx.bot._config.description.clear()
            ctx.bot.description = "Red V3"
            await ctx.send(_("Description reset."))
        elif len(description) > 250:  # While the limit is 256, we bold it adding characters.
            await ctx.send(
                _(
                    "This description is too long to properly display. "
                    "Please try again with below 250 characters."
                )
            )
        else:
            await ctx.bot._config.description.set(description)
            ctx.bot.description = description
            await ctx.tick()

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def addadminrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Adds an admin role for this guild.

        Admins have all the same access and Mods, plus additional admin level commands like:
         - `[p]set serverprefix`
         - `[p]addrole`
         - `[p]ban`
         - `[p]ignore guild`

         And more.

         **Examples:**
            - `[p]set addadminrole @Admins`
            - `[p]set addadminrole Super Admins`

        **Arguments:**
            - `<role>` - The role to add as an admin.
        """
        async with ctx.bot._config.guild(ctx.guild).admin_role() as roles:
            if role.id in roles:
                return await ctx.send(_("This role is already an admin role."))
            roles.append(role.id)
        await ctx.send(_("That role is now considered an admin role."))

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def addmodrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Adds a moderator role for this guild.

        This grants access to moderator level commands like:
         - `[p]mute`
         - `[p]cleanup`
         - `[p]customcommand create`

         And more.

         **Examples:**
            - `[p]set addmodrole @Mods`
            - `[p]set addmodrole Loyal Helpers`

        **Arguments:**
            - `<role>` - The role to add as a moderator.
        """
        async with ctx.bot._config.guild(ctx.guild).mod_role() as roles:
            if role.id in roles:
                return await ctx.send(_("This role is already a mod role."))
            roles.append(role.id)
        await ctx.send(_("That role is now considered a mod role."))

    @_set.command(aliases=["remadmindrole", "deladminrole", "deleteadminrole"])
    @checks.guildowner()
    @commands.guild_only()
    async def removeadminrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Removes an admin role for this guild.

        **Examples:**
            - `[p]set removeadminrole @Admins`
            - `[p]set removeadminrole Super Admins`

        **Arguments:**
            - `<role>` - The role to remove from being an admin.
        """
        async with ctx.bot._config.guild(ctx.guild).admin_role() as roles:
            if role.id not in roles:
                return await ctx.send(_("That role was not an admin role to begin with."))
            roles.remove(role.id)
        await ctx.send(_("That role is no longer considered an admin role."))

    @_set.command(aliases=["remmodrole", "delmodrole", "deletemodrole"])
    @checks.guildowner()
    @commands.guild_only()
    async def removemodrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Removes a mod role for this guild.

        **Examples:**
            - `[p]set removemodrole @Mods`
            - `[p]set removemodrole Loyal Helpers`

        **Arguments:**
            - `<role>` - The role to remove from being a moderator.
        """
        async with ctx.bot._config.guild(ctx.guild).mod_role() as roles:
            if role.id not in roles:
                return await ctx.send(_("That role was not a mod role to begin with."))
            roles.remove(role.id)
        await ctx.send(_("That role is no longer considered a mod role."))

    @_set.command(aliases=["usebotcolor"])
    @checks.guildowner()
    @commands.guild_only()
    async def usebotcolour(self, ctx: commands.Context):
        """
        Toggle whether to use the bot owner-configured colour for embeds.

        Default is to use the bot's configured colour.
        Otherwise, the colour used will be the colour of the bot's top role.

        **Example:**
            - `[p]set usebotcolour`
        """
        current_setting = await ctx.bot._config.guild(ctx.guild).use_bot_color()
        await ctx.bot._config.guild(ctx.guild).use_bot_color.set(not current_setting)
        await ctx.send(
            _("The bot {} use its configured color for embeds.").format(
                _("will not") if not current_setting else _("will")
            )
        )

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def serverfuzzy(self, ctx: commands.Context):
        """
        Toggle whether to enable fuzzy command search for the server.

        This allows the bot to identify potential misspelled commands and offer corrections.

        Note: This can be processor intensive and may be unsuitable for larger servers.

        Default is for fuzzy command search to be disabled.

        **Example:**
            - `[p]set serverfuzzy`
        """
        current_setting = await ctx.bot._config.guild(ctx.guild).fuzzy()
        await ctx.bot._config.guild(ctx.guild).fuzzy.set(not current_setting)
        await ctx.send(
            _("Fuzzy command search has been {} for this server.").format(
                _("disabled") if current_setting else _("enabled")
            )
        )

    @_set.command()
    @checks.is_owner()
    async def fuzzy(self, ctx: commands.Context):
        """
        Toggle whether to enable fuzzy command search in DMs.

        This allows the bot to identify potential misspelled commands and offer corrections.

        Default is for fuzzy command search to be disabled.

        **Example:**
            - `[p]set fuzzy`
        """
        current_setting = await ctx.bot._config.fuzzy()
        await ctx.bot._config.fuzzy.set(not current_setting)
        await ctx.send(
            _("Fuzzy command search has been {} in DMs.").format(
                _("disabled") if current_setting else _("enabled")
            )
        )

    @_set.command(aliases=["color"])
    @checks.is_owner()
    async def colour(self, ctx: commands.Context, *, colour: discord.Colour = None):
        """
        Sets a default colour to be used for the bot's embeds.

        Acceptable values for the colour parameter can be found at:

        https://discordpy.readthedocs.io/en/stable/ext/commands/api.html#discord.ext.commands.ColourConverter

        **Examples:**
            - `[p]set colour dark red`
            - `[p]set colour blurple`
            - `[p]set colour 0x5DADE2`
            - `[p]set color 0x#FDFEFE`
            - `[p]set color #7F8C8D`

        **Arguments:**
            - `[colour]` - The colour to use for embeds. Leave blank to set to the default value (red).
        """
        if colour is None:
            ctx.bot._color = discord.Color.red()
            await ctx.bot._config.color.set(discord.Color.red().value)
            return await ctx.send(_("The color has been reset."))
        ctx.bot._color = colour
        await ctx.bot._config.color.set(colour.value)
        await ctx.send(_("The color has been set."))

    @_set.group(invoke_without_command=True)
    @checks.is_owner()
    async def avatar(self, ctx: commands.Context, url: str = None):
        """Sets [botname]'s avatar

        Supports either an attachment or an image URL.

        **Examples:**
            - `[p]set avatar` - With an image attachment, this will set the avatar.
            - `[p]set avatar` - Without an attachment, this will show the command help.
            - `[p]set avatar https://links.flaree.xyz/k95` - Sets the avatar to the provided url.

        **Arguments:**
            - `[url]` - An image url to be used as an avatar. Leave blank when uploading an attachment.
        """
        if len(ctx.message.attachments) > 0:  # Attachments take priority
            data = await ctx.message.attachments[0].read()
        elif url is not None:
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        data = await r.read()
                except aiohttp.InvalidURL:
                    return await ctx.send(_("That URL is invalid."))
                except aiohttp.ClientError:
                    return await ctx.send(_("Something went wrong while trying to get the image."))
        else:
            await ctx.send_help()
            return

        try:
            async with ctx.typing():
                await ctx.bot.user.edit(avatar=data)
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Failed. Remember that you can edit my avatar "
                    "up to two times a hour. The URL or attachment "
                    "must be a valid image in either JPG or PNG format."
                )
            )
        except discord.InvalidArgument:
            await ctx.send(_("JPG / PNG format only."))
        else:
            await ctx.send(_("Done."))

    @avatar.command(name="remove", aliases=["clear"])
    @checks.is_owner()
    async def avatar_remove(self, ctx: commands.Context):
        """
        Removes [botname]'s avatar.

        **Example:**
            - `[p]set avatar remove`
        """
        async with ctx.typing():
            await ctx.bot.user.edit(avatar=None)
        await ctx.send(_("Avatar removed."))

    @_set.command(name="playing", aliases=["game"])
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _game(self, ctx: commands.Context, *, game: str = None):
        """Sets [botname]'s playing status.

        This will appear as `Playing <game>` or `PLAYING A GAME: <game>` depending on the context.

        Maximum length for a playing status is 128 characters.

        **Examples:**
            - `[p]set playing` - Clears the activity status.
            - `[p]set playing the keyboard`

        **Arguments:**
            - `[game]` - The text to follow `Playing`. Leave blank to clear the current activity status.
        """

        if game:
            if len(game) > 128:
                await ctx.send(_("The maximum length of game descriptions is 128 characters."))
                return
            game = discord.Game(name=game)
        else:
            game = None
        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        await ctx.bot.change_presence(status=status, activity=game)
        if game:
            await ctx.send(_("Status set to ``Playing {game.name}``.").format(game=game))
        else:
            await ctx.send(_("Game cleared."))

    @_set.command(name="listening")
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _listening(self, ctx: commands.Context, *, listening: str = None):
        """Sets [botname]'s listening status.

        This will appear as `Listening to <listening>`.

        Maximum length for a listening status is 128 characters.

        **Examples:**
            - `[p]set listening` - Clears the activity status.
            - `[p]set listening jams`

        **Arguments:**
            - `[listening]` - The text to follow `Listening to`. Leave blank to clear the current activity status."""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if listening:
            if len(listening) > 128:
                await ctx.send(
                    _("The maximum length of listening descriptions is 128 characters.")
                )
                return
            activity = discord.Activity(name=listening, type=discord.ActivityType.listening)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(
                _("Status set to ``Listening to {listening}``.").format(listening=listening)
            )
        else:
            await ctx.send(_("Listening cleared."))

    @_set.command(name="watching")
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _watching(self, ctx: commands.Context, *, watching: str = None):
        """Sets [botname]'s watching status.

        This will appear as `Watching <watching>`.

        Maximum length for a watching status is 128 characters.

        **Examples:**
            - `[p]set watching` - Clears the activity status.
            - `[p]set watching [p]help`

        **Arguments:**
            - `[watching]` - The text to follow `Watching`. Leave blank to clear the current activity status."""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if watching:
            if len(watching) > 128:
                await ctx.send(_("The maximum length of watching descriptions is 128 characters."))
                return
            activity = discord.Activity(name=watching, type=discord.ActivityType.watching)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(_("Status set to ``Watching {watching}``.").format(watching=watching))
        else:
            await ctx.send(_("Watching cleared."))

    @_set.command(name="competing")
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _competing(self, ctx: commands.Context, *, competing: str = None):
        """Sets [botname]'s competing status.

        This will appear as `Competing in <competing>`.

        Maximum length for a competing status is 128 characters.

        **Examples:**
            - `[p]set competing` - Clears the activity status.
            - `[p]set competing London 2012 Olympic Games`

        **Arguments:**
            - `[competing]` - The text to follow `Competing in`. Leave blank to clear the current activity status."""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if competing:
            if len(competing) > 128:
                await ctx.send(
                    _("The maximum length of competing descriptions is 128 characters.")
                )
                return
            activity = discord.Activity(name=competing, type=discord.ActivityType.competing)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(
                _("Status set to ``Competing in {competing}``.").format(competing=competing)
            )
        else:
            await ctx.send(_("Competing cleared."))

    @_set.command()
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def status(self, ctx: commands.Context, *, status: str):
        """Sets [botname]'s status.

        Available statuses:
            - `online`
            - `idle`
            - `dnd`
            - `invisible`

        **Examples:**
            - `[p]set status online` - Clears the status.
            - `[p]set status invisible`

        **Arguments:**
            - `<status>` - One of the available statuses.
        """

        statuses = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible,
        }

        game = ctx.bot.guilds[0].me.activity if len(ctx.bot.guilds) > 0 else None
        try:
            status = statuses[status.lower()]
        except KeyError:
            await ctx.send_help()
        else:
            await ctx.bot.change_presence(status=status, activity=game)
            await ctx.send(_("Status changed to {}.").format(status))

    @_set.command(
        name="streaming", aliases=["stream", "twitch"], usage="[(<streamer> <stream_title>)]"
    )
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def stream(self, ctx: commands.Context, streamer=None, *, stream_title=None):
        """Sets [botname]'s streaming status to a twitch stream.

        This will appear as `Streaming <stream_title>` or `LIVE ON TWITCH` depending on the context.
        It will also include a `Watch` button with a twitch.tv url for the provided streamer.

        Maximum length for a stream title is 128 characters.

        Leaving both streamer and stream_title empty will clear it.

        **Examples:**
            - `[p]set stream` - Clears the activity status.
            - `[p]set stream 26 Twentysix is streaming` - Sets the stream to `https://www.twitch.tv/26`.
            - `[p]set stream https://twitch.tv/26 Twentysix is streaming` - Sets the URL manually.

        **Arguments:**
            - `<streamer>` - The twitch streamer to provide a link to. This can be their twitch name or the entire URL.
            - `<stream_title>` - The text to follow `Streaming` in the status."""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else None

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
            if len(streamer) > 511:
                await ctx.send(_("The maximum length of the streamer url is 511 characters."))
                return
            if len(stream_title) > 128:
                await ctx.send(_("The maximum length of the stream title is 128 characters."))
                return
            activity = discord.Streaming(url=streamer, name=stream_title)
            await ctx.bot.change_presence(status=status, activity=activity)
        elif streamer is not None:
            await ctx.send_help()
            return
        else:
            await ctx.bot.change_presence(activity=None, status=status)
        await ctx.send(_("Done."))

    @_set.command(name="username", aliases=["name"])
    @checks.is_owner()
    async def _username(self, ctx: commands.Context, *, username: str):
        """Sets [botname]'s username.

        Maximum length for a username is 32 characters.

        Note: The username of a verified bot cannot be manually changed.
            Please contact Discord support to change it.

        **Example:**
            - `[p]set username BaguetteBot`

        **Arguments:**
            - `<username>` - The username to give the bot.
        """
        try:
            if self.bot.user.public_flags.verified_bot:
                await ctx.send(
                    _(
                        "The username of a verified bot cannot be manually changed."
                        " Please contact Discord support to change it."
                    )
                )
                return
            if len(username) > 32:
                await ctx.send(_("Failed to change name. Must be 32 characters or fewer."))
                return
            async with ctx.typing():
                await asyncio.wait_for(self._name(name=username), timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(
                _(
                    "Changing the username timed out. "
                    "Remember that you can only do it up to 2 times an hour."
                    " Use nicknames if you need frequent changes: {command}"
                ).format(command=inline(f"{ctx.clean_prefix}set nickname"))
            )
        except discord.HTTPException as e:
            if e.code == 50035:
                error_string = e.text.split("\n")[1]  # Remove the "Invalid Form body"
                await ctx.send(
                    _(
                        "Failed to change the username. "
                        "Discord returned the following error:\n"
                        "{error_message}"
                    ).format(error_message=inline(error_string))
                )
            else:
                log.error(
                    "Unexpected error occurred when trying to change the username.", exc_info=e
                )
                await ctx.send(_("Unexpected error occurred when trying to change the username."))
        else:
            await ctx.send(_("Done."))

    @_set.command(name="nickname")
    @checks.admin_or_permissions(manage_nicknames=True)
    @commands.guild_only()
    async def _nickname(self, ctx: commands.Context, *, nickname: str = None):
        """Sets [botname]'s nickname for the current server.

        Maximum length for a nickname is 32 characters.

        **Example:**
            - `[p]set nickname 🎃 SpookyBot 🎃`

        **Arguments:**
            - `[nickname]` - The nickname to give the bot. Leave blank to clear the current nickname.
        """
        try:
            if nickname and len(nickname) > 32:
                await ctx.send(_("Failed to change nickname. Must be 32 characters or fewer."))
                return
            await ctx.guild.me.edit(nick=nickname)
        except discord.Forbidden:
            await ctx.send(_("I lack the permissions to change my own nickname."))
        else:
            await ctx.send(_("Done."))

    @_set.command(aliases=["prefixes"], require_var_positional=True)
    @checks.is_owner()
    async def prefix(self, ctx: commands.Context, *prefixes: str):
        """Sets [botname]'s global prefix(es).

        Warning: This is not additive. It will replace all current prefixes.

        See also the `--mentionable` flag to enable mentioning the bot as the prefix.

        **Examples:**
            - `[p]set prefix !`
            - `[p]set prefix "! "` - Quotes are needed to use spaces in prefixes.
            - `[p]set prefix "@[botname] "` - This uses a mention as the prefix. See also the `--mentionable` flag.
            - `[p]set prefix ! ? .` - Sets multiple prefixes.

        **Arguments:**
            - `<prefixes...>` - The prefixes the bot will respond to globally.
        """
        await ctx.bot.set_prefixes(guild=None, prefixes=prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Prefix set."))
        else:
            await ctx.send(_("Prefixes set."))

    @_set.command(aliases=["serverprefixes"])
    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    async def serverprefix(self, ctx: commands.Context, *prefixes: str):
        """
        Sets [botname]'s server prefix(es).

        Warning: This will override global prefixes, the bot will not respond to any global prefixes in this server.
            This is not additive. It will replace all current server prefixes.

        **Examples:**
            - `[p]set serverprefix !`
            - `[p]set serverprefix "! "` - Quotes are needed to use spaces in prefixes.
            - `[p]set serverprefix "@[botname] "` - This uses a mention as the prefix.
            - `[p]set serverprefix ! ? .` - Sets multiple prefixes.

        **Arguments:**
            - `[prefixes...]` - The prefixes the bot will respond to on this server. Leave blank to clear server prefixes.
        """
        if not prefixes:
            await ctx.bot.set_prefixes(guild=ctx.guild, prefixes=[])
            await ctx.send(_("Server prefixes have been reset."))
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Server prefix set."))
        else:
            await ctx.send(_("Server prefixes set."))

    @_set.command()
    @checks.is_owner()
    async def globallocale(self, ctx: commands.Context, language_code: str):
        """
        Changes the bot's default locale.

        This will be used when a server has not set a locale, or in DMs.

        Go to [Red's Crowdin page](https://translate.discord.red) to see locales that are available with translations.

        To reset to English, use "en-US".

        **Examples:**
            - `[p]set locale en-US`
            - `[p]set locale de-DE`
            - `[p]set locale fr-FR`
            - `[p]set locale pl-PL`

        **Arguments:**
            - `<language_code>` - The default locale to use for the bot. This can be any language code with country code included.
        """
        try:
            locale = BabelLocale.parse(language_code, sep="-")
        except (ValueError, UnknownLocaleError):
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        if locale.territory is None:
            await ctx.send(
                _("Invalid format - language code has to include country code, e.g. `en-US`")
            )
            return
        standardized_locale_name = f"{locale.language}-{locale.territory}"
        i18n.set_locale(standardized_locale_name)
        await self.bot._i18n_cache.set_locale(None, standardized_locale_name)
        await i18n.set_contextual_locales_from_guild(self.bot, ctx.guild)
        await ctx.send(_("Global locale has been set."))

    @_set.command()
    @commands.guild_only()
    @checks.guildowner_or_permissions(manage_guild=True)
    async def locale(self, ctx: commands.Context, language_code: str):
        """
        Changes the bot's locale in this server.

        Go to [Red's Crowdin page](https://translate.discord.red) to see locales that are available with translations.

        Use "default" to return to the bot's default set language.
        To reset to English, use "en-US".

        **Examples:**
            - `[p]set locale en-US`
            - `[p]set locale de-DE`
            - `[p]set locale fr-FR`
            - `[p]set locale pl-PL`
            - `[p]set locale default` - Resets to the global default locale.

        **Arguments:**
            - `<language_code>` - The default locale to use for the bot. This can be any language code with country code included.
        """
        if language_code.lower() == "default":
            global_locale = await self.bot._config.locale()
            i18n.set_contextual_locale(global_locale)
            await self.bot._i18n_cache.set_locale(ctx.guild, None)
            await ctx.send(_("Locale has been set to the default."))
            return
        try:
            locale = BabelLocale.parse(language_code, sep="-")
        except (ValueError, UnknownLocaleError):
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        if locale.territory is None:
            await ctx.send(
                _("Invalid format - language code has to include country code, e.g. `en-US`")
            )
            return
        standardized_locale_name = f"{locale.language}-{locale.territory}"
        i18n.set_contextual_locale(standardized_locale_name)
        await self.bot._i18n_cache.set_locale(ctx.guild, standardized_locale_name)
        await ctx.send(_("Locale has been set."))

    @_set.command(aliases=["globalregion"])
    @commands.guild_only()
    @checks.is_owner()
    async def globalregionalformat(self, ctx: commands.Context, language_code: str = None):
        """
        Changes bot's regional format. This is used for formatting date, time and numbers.

        `language_code` can be any language code with country code included, e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.
        Leave `language_code` empty to base regional formatting on bot's locale.

        **Examples:**
            - `[p]set globalregionalformat en-US`
            - `[p]set globalregion de-DE`
            - `[p]set globalregionalformat` - Resets to the locale.

        **Arguments:**
            - `[language_code]` - The default region format to use for the bot.
        """
        if language_code is None:
            i18n.set_regional_format(None)
            await self.bot._i18n_cache.set_regional_format(None, None)
            await ctx.send(_("Global regional formatting will now be based on bot's locale."))
            return

        try:
            locale = BabelLocale.parse(language_code, sep="-")
        except (ValueError, UnknownLocaleError):
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        if locale.territory is None:
            await ctx.send(
                _("Invalid format - language code has to include country code, e.g. `en-US`")
            )
            return
        standardized_locale_name = f"{locale.language}-{locale.territory}"
        i18n.set_regional_format(standardized_locale_name)
        await self.bot._i18n_cache.set_regional_format(None, standardized_locale_name)
        await ctx.send(
            _("Global regional formatting will now be based on `{language_code}` locale.").format(
                language_code=standardized_locale_name
            )
        )

    @_set.command(aliases=["region"])
    @checks.guildowner_or_permissions(manage_guild=True)
    async def regionalformat(self, ctx: commands.Context, language_code: str = None):
        """
        Changes bot's regional format in this server. This is used for formatting date, time and numbers.

        `language_code` can be any language code with country code included, e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.
        Leave `language_code` empty to base regional formatting on bot's locale in this server.

        **Examples:**
            - `[p]set regionalformat en-US`
            - `[p]set region de-DE`
            - `[p]set regionalformat` - Resets to the locale.

        **Arguments:**
            - `[language_code]` - The region format to use for the bot in this server.
        """
        if language_code is None:
            i18n.set_contextual_regional_format(None)
            await self.bot._i18n_cache.set_regional_format(ctx.guild, None)
            await ctx.send(
                _("Regional formatting will now be based on bot's locale in this server.")
            )
            return

        try:
            locale = BabelLocale.parse(language_code, sep="-")
        except (ValueError, UnknownLocaleError):
            await ctx.send(_("Invalid language code. Use format: `en-US`"))
            return
        if locale.territory is None:
            await ctx.send(
                _("Invalid format - language code has to include country code, e.g. `en-US`")
            )
            return
        standardized_locale_name = f"{locale.language}-{locale.territory}"
        i18n.set_contextual_regional_format(standardized_locale_name)
        await self.bot._i18n_cache.set_regional_format(ctx.guild, standardized_locale_name)
        await ctx.send(
            _("Regional formatting will now be based on `{language_code}` locale.").format(
                language_code=standardized_locale_name
            )
        )

    @_set.command()
    @checks.is_owner()
    async def custominfo(self, ctx: commands.Context, *, text: str = None):
        """Customizes a section of `[p]info`.

        The maximum amount of allowed characters is 1024.
        Supports markdown, links and "mentions".

        Link example: `[My link](https://example.com)`

        **Examples:**
            - `[p]set custominfo >>> I can use **markdown** such as quotes, ||spoilers|| and multiple lines.`
            - `[p]set custominfo Join my [support server](discord.gg/discord)!`
            - `[p]set custominfo` - Removes custom info text.

        **Arguments:**
            - `[text]` - The custom info text.
        """
        if not text:
            await ctx.bot._config.custom_info.clear()
            await ctx.send(_("The custom text has been cleared."))
            return
        if len(text) <= 1024:
            await ctx.bot._config.custom_info.set(text)
            await ctx.send(_("The custom text has been set."))
            await ctx.invoke(self.info)
        else:
            await ctx.send(_("Text must be fewer than 1024 characters long."))

    @_set.group(invoke_without_command=True)
    @checks.is_owner()
    async def api(self, ctx: commands.Context, service: str, *, tokens: TokenConverter):
        """
        Commands to set, list or remove various external API tokens.

        This setting will be asked for by some 3rd party cogs and some core cogs.

        To add the keys provide the service name and the tokens as a comma separated
        list of key,values as described by the cog requesting this command.

        Note: API tokens are sensitive, so this command should only be used in a private channel or in DM with the bot.

        **Examples:**
            - `[p]set api Spotify redirect_uri localhost`
            - `[p]set api github client_id,whoops client_secret,whoops`

        **Arguments:**
            - `<service>` - The service you're adding tokens to.
            - `<tokens>` - Pairs of token keys and values. The key and value should be separated by one of ` `, `,`, or `;`.
        """
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await ctx.message.delete()
        await ctx.bot.set_shared_api_tokens(service, **tokens)
        await ctx.send(_("`{service}` API tokens have been set.").format(service=service))

    @api.command(name="list")
    async def api_list(self, ctx: commands.Context):
        """
        Show all external API services along with their keys that have been set.

        Secrets are not shown.

        **Example:**
            - `[p]set api list``
        """

        services: dict = await ctx.bot.get_shared_api_tokens()
        if not services:
            await ctx.send(_("No API services have been set yet."))
            return

        sorted_services = sorted(services.keys(), key=str.lower)

        joined = _("Set API services:\n") if len(services) > 1 else _("Set API service:\n")
        for service_name in sorted_services:
            joined += "+ {}\n".format(service_name)
            for key_name in services[service_name].keys():
                joined += "  - {}\n".format(key_name)
        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @api.command(name="remove", require_var_positional=True)
    async def api_remove(self, ctx: commands.Context, *services: str):
        """
        Remove the given services with all their keys and tokens.

        **Examples:**
            - `[p]set api remove Spotify`
            - `[p]set api remove github audiodb`

        **Arguments:**
            - `<services...>` - The services to remove."""
        bot_services = (await ctx.bot.get_shared_api_tokens()).keys()
        services = [s for s in services if s in bot_services]

        if services:
            await self.bot.remove_shared_api_services(*services)
            if len(services) > 1:
                msg = _("Services deleted successfully:\n{services_list}").format(
                    services_list=humanize_list(services)
                )
            else:
                msg = _("Service deleted successfully: {service_name}").format(
                    service_name=services[0]
                )
            await ctx.send(msg)
        else:
            await ctx.send(_("None of the services you provided had any keys set."))

    @commands.group()
    @checks.is_owner()
    async def helpset(self, ctx: commands.Context):
        """
        Commands to manage settings for the help command.

        All help settings are applied globally.
        """
        pass

    @helpset.command(name="showsettings")
    async def helpset_showsettings(self, ctx: commands.Context):
        """
        Show the current help settings.

        Warning: These settings may not be accurate if the default formatter is not in use.

        **Example:**
            - `[p]helpset showsettings``
        """

        help_settings = await commands.help.HelpSettings.from_context(ctx)

        if type(ctx.bot._help_formatter) is commands.help.RedHelpFormatter:
            message = help_settings.pretty
        else:
            message = _(
                "Warning: The default formatter is not in use, these settings may not apply."
            )
            message += f"\n\n{help_settings.pretty}"

        for page in pagify(message):
            await ctx.send(page)

    @helpset.command(name="resetformatter")
    async def helpset_resetformatter(self, ctx: commands.Context):
        """
        This resets [botname]'s help formatter to the default formatter.

        **Example:**
            - `[p]helpset resetformatter``
        """

        ctx.bot.reset_help_formatter()
        await ctx.send(
            _(
                "The help formatter has been reset. "
                "This will not prevent cogs from modifying help, "
                "you may need to remove a cog if this has been an issue."
            )
        )

    @helpset.command(name="resetsettings")
    async def helpset_resetsettings(self, ctx: commands.Context):
        """
        This resets [botname]'s help settings to their defaults.

        This may not have an impact when using custom formatters from 3rd party cogs

        **Example:**
            - `[p]helpset resetsettings``
        """
        await ctx.bot._config.help.clear()
        await ctx.send(
            _(
                "The help settings have been reset to their defaults. "
                "This may not have an impact when using 3rd party help formatters."
            )
        )

    @helpset.command(name="usemenus")
    async def helpset_usemenus(self, ctx: commands.Context, use_menus: bool = None):
        """
        Allows the help command to be sent as a paginated menu instead of separate
        messages.

        When enabled, `[p]help` will only show one page at a time and will use reactions to navigate between pages.

        This defaults to False.
        Using this without a setting will toggle.

         **Examples:**
            - `[p]helpset usemenues True` - Enables using menus.
            - `[p]helpset usemenues` - Toggles the value.

        **Arguments:**
            - `[use_menus]` - Whether to use menus. Leave blank to toggle.
        """
        if use_menus is None:
            use_menus = not await ctx.bot._config.help.use_menus()
        await ctx.bot._config.help.use_menus.set(use_menus)
        if use_menus:
            await ctx.send(_("Help will use menus."))
        else:
            await ctx.send(_("Help will not use menus."))

    @helpset.command(name="showhidden")
    async def helpset_showhidden(self, ctx: commands.Context, show_hidden: bool = None):
        """
        This allows the help command to show hidden commands.

        This defaults to False.
        Using this without a setting will toggle.

        **Examples:**
            - `[p]helpset showhidden True` - Enables showing hidden commands.
            - `[p]helpset showhidden` - Toggles the value.

        **Arguments:**
            - `[show_hidden]` - Whether to use show hidden commands in help. Leave blank to toggle.
        """
        if show_hidden is None:
            show_hidden = not await ctx.bot._config.help.show_hidden()
        await ctx.bot._config.help.show_hidden.set(show_hidden)
        if show_hidden:
            await ctx.send(_("Help will not filter hidden commands."))
        else:
            await ctx.send(_("Help will filter hidden commands."))

    @helpset.command(name="showaliases")
    async def helpset_showaliases(self, ctx: commands.Context, show_aliases: bool = None):
        """
        This allows the help command to show existing commands aliases if there is any.

        This defaults to True.
        Using this without a setting will toggle.

        **Examples:**
            - `[p]helpset showaliases False` - Disables showing aliases on this server.
            - `[p]helpset showaliases` - Toggles the value.

        **Arguments:**
            - `[show_aliases]` - Whether to include aliases in help. Leave blank to toggle.
        """
        if show_aliases is None:
            show_aliases = not await ctx.bot._config.help.show_aliases()
        await ctx.bot._config.help.show_aliases.set(show_aliases)
        if show_aliases:
            await ctx.send(_("Help will show commands aliases."))
        else:
            await ctx.send(_("Help will not show commands aliases."))

    @helpset.command(name="usetick")
    async def helpset_usetick(self, ctx: commands.Context, use_tick: bool = None):
        """
        This allows the help command message to be ticked if help is sent to a DM.

        Ticking is reacting to the help message with a ✅.

        Defaults to False.
        Using this without a setting will toggle.

        Note: This is only used when the bot is not using menus.

        **Examples:**
            - `[p]helpset usetick False` - Disables ticking when help is sent to DMs.
            - `[p]helpset usetick` - Toggles the value.

        **Arguments:**
            - `[use_tick]` - Whether to tick the help command when help is sent to DMs. Leave blank to toggle.
        """
        if use_tick is None:
            use_tick = not await ctx.bot._config.help.use_tick()
        await ctx.bot._config.help.use_tick.set(use_tick)
        if use_tick:
            await ctx.send(_("Help will now tick the command when sent in a DM."))
        else:
            await ctx.send(_("Help will not tick the command when sent in a DM."))

    @helpset.command(name="verifychecks")
    async def helpset_permfilter(self, ctx: commands.Context, verify: bool = None):
        """
        Sets if commands which can't be run in the current context should be filtered from help.

        Defaults to True.
        Using this without a setting will toggle.

        **Examples:**
            - `[p]helpset verifychecks False` - Enables showing unusable commands in help.
            - `[p]helpset verifychecks` - Toggles the value.

        **Arguments:**
            - `[verify]` - Whether to hide unusable commands in help. Leave blank to toggle.
        """
        if verify is None:
            verify = not await ctx.bot._config.help.verify_checks()
        await ctx.bot._config.help.verify_checks.set(verify)
        if verify:
            await ctx.send(_("Help will only show for commands which can be run."))
        else:
            await ctx.send(_("Help will show up without checking if the commands can be run."))

    @helpset.command(name="verifyexists")
    async def helpset_verifyexists(self, ctx: commands.Context, verify: bool = None):
        """
        Sets whether the bot should respond to help commands for nonexistent topics.

        When enabled, this will indicate the existence of help topics, even if the user can't use it.

        Note: This setting on its own does not fully prevent command enumeration.

        Defaults to False.
        Using this without a setting will toggle.

        **Examples:**
            - `[p]helpset verifyexists True` - Enables sending help for nonexistent topics.
            - `[p]helpset verifyexists` - Toggles the value.

        **Arguments:**
            - `[verify]` - Whether to respond to help for nonexistent topics. Leave blank to toggle.
        """
        if verify is None:
            verify = not await ctx.bot._config.help.verify_exists()
        await ctx.bot._config.help.verify_exists.set(verify)
        if verify:
            await ctx.send(_("Help will verify the existence of help topics."))
        else:
            await ctx.send(
                _(
                    "Help will only verify the existence of "
                    "help topics via fuzzy help (if enabled)."
                )
            )

    @helpset.command(name="pagecharlimit")
    async def helpset_pagecharlimt(self, ctx: commands.Context, limit: int):
        """Set the character limit for each page in the help message.

        Note: This setting only applies to embedded help.

        The default value is 1000 characters. The minimum value is 500.
        The maximum is based on the lower of what you provide and what discord allows.

        Please note that setting a relatively small character limit may
        mean some pages will exceed this limit.

        **Example:**
            - `[p]helpset pagecharlimit 1500`

        **Arguments:**
            - `<limit>` - The max amount of characters to show per page in the help message.
        """
        if limit < 500:
            await ctx.send(_("You must give a value of at least 500 characters."))
            return

        await ctx.bot._config.help.page_char_limit.set(limit)
        await ctx.send(_("Done. The character limit per page has been set to {}.").format(limit))

    @helpset.command(name="maxpages")
    async def helpset_maxpages(self, ctx: commands.Context, pages: int):
        """Set the maximum number of help pages sent in a server channel.

        Note: This setting does not apply to menu help.

        If a help message contains more pages than this value, the help message will
        be sent to the command author via DM. This is to help reduce spam in server
        text channels.

        The default value is 2 pages.

        **Examples:**
            - `[p]helpset maxpages 50` - Basically never send help to DMs.
            - `[p]helpset maxpages 0` - Always send help to DMs.

        **Arguments:**
            - `<limit>` - The max pages allowed to send per help in a server.
        """
        if pages < 0:
            await ctx.send(_("You must give a value of zero or greater!"))
            return

        await ctx.bot._config.help.max_pages_in_guild.set(pages)
        await ctx.send(_("Done. The page limit has been set to {}.").format(pages))

    @helpset.command(name="deletedelay")
    @commands.bot_has_permissions(manage_messages=True)
    async def helpset_deletedelay(self, ctx: commands.Context, seconds: int):
        """Set the delay after which help pages will be deleted.

        The setting is disabled by default, and only applies to non-menu help,
        sent in server text channels.
        Setting the delay to 0 disables this feature.

        The bot has to have MANAGE_MESSAGES permission for this to work.

        **Examples:**
            - `[p]helpset deletedelay 60` - Delete the help pages after a minute.
            - `[p]helpset deletedelay 1` - Delete the help pages as quickly as possible.
            - `[p]helpset deletedelay 1209600` - Max time to wait before deleting (14 days).
            - `[p]helpset deletedelay 0` - Disable deleting help pages.

        **Arguments:**
            - `<seconds>` - The seconds to wait before deleting help pages.
        """
        if seconds < 0:
            await ctx.send(_("You must give a value of zero or greater!"))
            return
        if seconds > 60 * 60 * 24 * 14:  # 14 days
            await ctx.send(_("The delay cannot be longer than 14 days!"))
            return

        await ctx.bot._config.help.delete_delay.set(seconds)
        if seconds == 0:
            await ctx.send(_("Done. Help messages will not be deleted now."))
        else:
            await ctx.send(_("Done. The delete delay has been set to {} seconds.").format(seconds))

    @helpset.command(name="tagline")
    async def helpset_tagline(self, ctx: commands.Context, *, tagline: str = None):
        """
        Set the tagline to be used.

        The maximum tagline length is 2048 characters.
        This setting only applies to embedded help. If no tagline is specified, the default will be used instead.

        **Examples:**
            - `[p]helpset tagline Thanks for using the bot!`
            - `[p]helpset tagline` - Resets the tagline to the default.

        **Arguments:**
            - `[tagline]` - The tagline to appear at the bottom of help embeds. Leave blank to reset.
        """
        if tagline is None:
            await ctx.bot._config.help.tagline.set("")
            return await ctx.send(_("The tagline has been reset."))

        if len(tagline) > 2048:
            await ctx.send(
                _(
                    "Your tagline is too long! Please shorten it to be "
                    "no more than 2048 characters long."
                )
            )
            return

        await ctx.bot._config.help.tagline.set(tagline)
        await ctx.send(_("The tagline has been set."))

    @commands.command(cooldown_after_parsing=True)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def contact(self, ctx: commands.Context, *, message: str):
        """Sends a message to the owner.

        This is limited to one message every 60 seconds per person.

        **Example:**
            - `[p]contact Help! The bot has become sentient!`

        **Arguments:**
            - `[message]` - The message to send to the owner.
        """
        guild = ctx.message.guild
        author = ctx.message.author
        footer = _("User ID: {}").format(author.id)

        if ctx.guild is None:
            source = _("through DM")
        else:
            source = _("from {}").format(guild)
            footer += _(" | Server ID: {}").format(guild.id)

        prefixes = await ctx.bot.get_valid_prefixes()
        prefix = re.sub(rf"<@!?{ctx.me.id}>", f"@{ctx.me.name}".replace("\\", r"\\"), prefixes[0])

        content = _("Use `{}dm {} <text>` to reply to this user").format(prefix, author.id)

        description = _("Sent by {} {}").format(author, source)

        destinations = await ctx.bot.get_owner_notification_destinations()

        if not destinations:
            await ctx.send(_("I've been configured not to send this anywhere."))
            return

        successful = False

        for destination in destinations:

            is_dm = isinstance(destination, discord.User)
            send_embed = None

            if is_dm:
                send_embed = await ctx.bot._config.user(destination).embeds()
            else:
                if not destination.permissions_for(destination.guild.me).send_messages:
                    continue
                if destination.permissions_for(destination.guild.me).embed_links:
                    send_embed = await ctx.bot._config.channel(destination).embeds()
                    if send_embed is None:
                        send_embed = await ctx.bot._config.guild(destination.guild).embeds()
                else:
                    send_embed = False

            if send_embed is None:
                send_embed = await ctx.bot._config.embeds()

            if send_embed:

                if not is_dm:
                    color = await ctx.bot.get_embed_color(destination)
                else:
                    color = ctx.bot._color

                e = discord.Embed(colour=color, description=message)
                if author.avatar_url:
                    e.set_author(name=description, icon_url=author.avatar_url)
                else:
                    e.set_author(name=description)

                e.set_footer(text=footer)

                try:
                    await destination.send(embed=e)
                except discord.Forbidden:
                    log.exception(f"Contact failed to {destination}({destination.id})")
                    # Should this automatically opt them out?
                except discord.HTTPException:
                    log.exception(
                        f"An unexpected error happened while attempting to"
                        f" send contact to {destination}({destination.id})"
                    )
                else:
                    successful = True

            else:

                msg_text = "{}\nMessage:\n\n{}\n{}".format(description, message, footer)

                try:
                    await destination.send("{}\n{}".format(content, box(msg_text)))
                except discord.Forbidden:
                    log.exception(f"Contact failed to {destination}({destination.id})")
                    # Should this automatically opt them out?
                except discord.HTTPException:
                    log.exception(
                        f"An unexpected error happened while attempting to"
                        f" send contact to {destination}({destination.id})"
                    )
                else:
                    successful = True

        if successful:
            await ctx.send(_("Your message has been sent."))
        else:
            await ctx.send(_("I'm unable to deliver your message. Sorry."))

    @commands.command()
    @checks.is_owner()
    async def dm(self, ctx: commands.Context, user_id: int, *, message: str):
        """Sends a DM to a user.

        This command needs a user ID to work.

        To get a user ID, go to Discord's settings and open the 'Appearance' tab.
        Enable 'Developer Mode', then right click a user and click on 'Copy ID'.

        **Example:**
            - `[p]dm 262626262626262626 Do you like me? Yes / No`

        **Arguments:**
            - `[message]` - The message to dm to the user.
        """
        destination = self.bot.get_user(user_id)
        if destination is None or destination.bot:
            await ctx.send(
                _(
                    "Invalid ID, user not found, or user is a bot. "
                    "You can only send messages to people I share "
                    "a server with."
                )
            )
            return

        prefixes = await ctx.bot.get_valid_prefixes()
        prefix = re.sub(rf"<@!?{ctx.me.id}>", f"@{ctx.me.name}".replace("\\", r"\\"), prefixes[0])
        description = _("Owner of {}").format(ctx.bot.user)
        content = _("You can reply to this message with {}contact").format(prefix)
        if await ctx.embed_requested():
            e = discord.Embed(colour=discord.Colour.red(), description=message)

            e.set_footer(text=content)
            if ctx.bot.user.avatar_url:
                e.set_author(name=description, icon_url=ctx.bot.user.avatar_url)
            else:
                e.set_author(name=description)

            try:
                await destination.send(embed=e)
            except discord.HTTPException:
                await ctx.send(
                    _("Sorry, I couldn't deliver your message to {}").format(destination)
                )
            else:
                await ctx.send(_("Message delivered to {}").format(destination))
        else:
            response = "{}\nMessage:\n\n{}".format(description, message)
            try:
                await destination.send("{}\n{}".format(box(response), content))
            except discord.HTTPException:
                await ctx.send(
                    _("Sorry, I couldn't deliver your message to {}").format(destination)
                )
            else:
                await ctx.send(_("Message delivered to {}").format(destination))

    @commands.command(hidden=True)
    @checks.is_owner()
    async def datapath(self, ctx: commands.Context):
        """Prints the bot's data path."""
        from redbot.core.data_manager import basic_config

        data_dir = Path(basic_config["DATA_PATH"])
        msg = _("Data path: {path}").format(path=data_dir)
        await ctx.send(box(msg))

    @commands.command(hidden=True)
    @checks.is_owner()
    async def debuginfo(self, ctx: commands.Context):
        """Shows debug information useful for debugging."""

        if sys.platform == "linux":
            import distro  # pylint: disable=import-error

        IS_WINDOWS = os.name == "nt"
        IS_MAC = sys.platform == "darwin"
        IS_LINUX = sys.platform == "linux"

        pyver = "{}.{}.{} ({})".format(*sys.version_info[:3], platform.architecture()[0])
        pipver = pip.__version__
        redver = red_version_info
        dpy_version = discord.__version__
        if IS_WINDOWS:
            os_info = platform.uname()
            osver = "{} {} (version {})".format(os_info.system, os_info.release, os_info.version)
        elif IS_MAC:
            os_info = platform.mac_ver()
            osver = "Mac OSX {} {}".format(os_info[0], os_info[2])
        elif IS_LINUX:
            os_info = distro.linux_distribution()
            osver = "{} {}".format(os_info[0], os_info[1]).strip()
        else:
            osver = "Could not parse OS, report this on Github."
        user_who_ran = getpass.getuser()
        driver = storage_type()

        from redbot.core.data_manager import basic_config, config_file

        data_path = Path(basic_config["DATA_PATH"])
        disabled_intents = (
            ", ".join(
                intent_name.replace("_", " ").title()
                for intent_name, enabled in self.bot.intents
                if not enabled
            )
            or "None"
        )
        if await ctx.embed_requested():
            e = discord.Embed(color=await ctx.embed_colour())
            e.title = "Debug Info for Red"
            e.add_field(name="Red version", value=redver, inline=True)
            e.add_field(name="Python version", value=pyver, inline=True)
            e.add_field(name="Discord.py version", value=dpy_version, inline=True)
            e.add_field(name="Pip version", value=pipver, inline=True)
            e.add_field(name="System arch", value=platform.machine(), inline=True)
            e.add_field(name="User", value=user_who_ran, inline=True)
            e.add_field(name="Storage type", value=driver, inline=True)
            e.add_field(name="Disabled intents", value=disabled_intents, inline=True)
            e.add_field(name="OS version", value=osver, inline=False)
            e.add_field(
                name="Python executable",
                value=escape(sys.executable, formatting=True),
                inline=False,
            )
            e.add_field(
                name="Data path",
                value=escape(str(data_path), formatting=True),
                inline=False,
            )
            e.add_field(
                name="Metadata file",
                value=escape(str(config_file), formatting=True),
                inline=False,
            )
            await ctx.send(embed=e)
        else:
            info = (
                "Debug Info for Red\n\n"
                + "Red version: {}\n".format(redver)
                + "Python version: {}\n".format(pyver)
                + "Discord.py version: {}\n".format(dpy_version)
                + "Pip version: {}\n".format(pipver)
                + "System arch: {}\n".format(platform.machine())
                + "User: {}\n".format(user_who_ran)
                + "OS version: {}\n".format(osver)
                + "Storage type: {}\n".format(driver)
                + "Disabled intents: {}\n".format(disabled_intents)
                + "Python executable: {}\n".format(sys.executable)
                + "Data path: {}\n".format(data_path)
                + "Metadata file: {}\n".format(config_file)
            )
            await ctx.send(box(info))

    @commands.group(aliases=["whitelist"])
    @checks.is_owner()
    async def allowlist(self, ctx: commands.Context):
        """
        Commands to manage the allowlist.

        Warning: When the allowlist is in use, the bot will ignore commands from everyone not on the list.

        Use `[p]allowlist clear` to disable the allowlist
        """
        pass

    @allowlist.command(name="add", require_var_positional=True)
    async def allowlist_add(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Adds users to the allowlist.

        **Examples:**
            - `[p]allowlist add @26 @Will` - Adds two users to the allowlist.
            - `[p]allowlist add 262626262626262626` - Adds a user by ID.

        **Arguments:**
            - `<users...>` - The user or users to add to the allowlist.
        """
        uids = {getattr(user, "id", user) for user in users}
        await self.bot.add_to_allowlist_raw(uids, None)
        if len(uids) > 1:
            await ctx.send(_("Users have been added to the allowlist."))
        else:
            await ctx.send(_("User has been added to the allowlist."))
        await ctx.send(_("Users added to allowlist."))

    @allowlist.command(name="list")
    async def allowlist_list(self, ctx: commands.Context):
        """
        Lists users on the allowlist.

        **Example:**
            - `[p]allowlist list`
        """
        curr_list = await ctx.bot._config.whitelist()

        if not curr_list:
            await ctx.send("Allowlist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Users on the allowlist:")
        else:
            msg = _("User on the allowlist:")
        for user_id in curr_list:
            user = self.bot.get_user(user_id)
            if not user:
                user = _("Unknown or Deleted User")
            msg += f"\n\t- {user_id} ({user})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @allowlist.command(name="remove", require_var_positional=True)
    async def allowlist_remove(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Removes users from the allowlist.

        The allowlist will be disabled if all users are removed.

        **Examples:**
            - `[p]allowlist remove @26 @Will` - Removes two users from the allowlist.
            - `[p]allowlist remove 262626262626262626` - Removes a user by ID.

        **Arguments:**
            - `<users...>` - The user or users to remove from the allowlist.
        """
        uids = {getattr(user, "id", user) for user in users}
<<<<<<< HEAD
        await self.bot.remove_from_allowlist(uids, None)
=======
        await self.bot.remove_from_allowlist_raw(uids, None)

>>>>>>> 4912fb74 (Fix crash on localallowlist remove <user/role> reported by fixator)
        if len(uids) > 1:
            await ctx.send(_("Users have been removed from the allowlist."))
        else:
            await ctx.send(_("User has been removed from the allowlist."))

    @allowlist.command(name="clear")
    async def allowlist_clear(self, ctx: commands.Context):
        """
        Clears the allowlist.

        This disables the allowlist.

        **Example:**
            - `[p]allowlist clear`
        """
        await self.bot._whiteblacklist_cache.clear_whitelist()
        await ctx.send(_("Allowlist has been cleared."))

    @commands.group(aliases=["blacklist", "denylist"])
    @checks.is_owner()
    async def blocklist(self, ctx: commands.Context):
        """
        Commands to manage the blocklist.

        Use `[p]blocklist clear` to disable the blocklist
        """
        pass

    @blocklist.command(name="add", require_var_positional=True)
    async def blocklist_add(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Adds users to the blocklist.

        **Examples:**
            - `[p]blocklist add @26 @Will` - Adds two users to the blocklist.
            - `[p]blocklist add 262626262626262626` - Blocks a user by ID.

        **Arguments:**
            - `<users...>` - The user or users to add to the blocklist.
        """
        for user in users:
            if isinstance(user, int):
                user_obj = discord.Object(id=user)
            else:
                user_obj = user
            if await ctx.bot.is_owner(user_obj):
                await ctx.send(_("You cannot add an owner to the blocklist!"))
                return

        uids = {getattr(user, "id", user) for user in users}
        await self.bot.add_to_blocklist_raw(uids, None)
        if len(uids) > 1:
            await ctx.send(_("Users have been added to the blocklist."))
        else:
            await ctx.send(_("User has been added to the blocklist."))

    @blocklist.command(name="list")
    async def blocklist_list(self, ctx: commands.Context):
        """
        Lists users on the blocklist.

        **Example:**
            - `[p]blocklist list`
        """
        curr_list = await self.bot._whiteblacklist_cache.get_blacklist(None)

        if not curr_list:
            await ctx.send("Blocklist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Users on the blocklist:")
        else:
            msg = _("User on the blocklist:")
        for user_id in curr_list:
            user = self.bot.get_user(user_id)
            if not user:
                user = _("Unknown or Deleted User")
            msg += f"\n\t- {user_id} ({user})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @blocklist.command(name="remove", require_var_positional=True)
    async def blocklist_remove(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Removes users from the blocklist.

        **Examples:**
            - `[p]blocklist remove @26 @Will` - Removes two users from the blocklist.
            - `[p]blocklist remove 262626262626262626` - Removes a user by ID.

        **Arguments:**
            - `<users...>` - The user or users to remove from the blocklist.
        """
        uids = {getattr(user, "id", user) for user in users}
        await self.bot.remove_from_blocklist_raw(uids, None)
        await self.bot._whiteblacklist_cache.remove_from_blacklist(None, uids)
        if len(uids) > 1:
            await ctx.send(_("Users have been removed from the blocklist."))
        else:
            await ctx.send(_("User has been removed from the blocklist."))

    @blocklist.command(name="clear")
    async def blocklist_clear(self, ctx: commands.Context):
        """
        Clears the blocklist.

        **Example:**
            - `[p]blocklist clear`
        """
        await self.bot._whiteblacklist_cache.clear_blacklist()
        await ctx.send(_("Blocklist has been cleared."))

    @commands.group(aliases=["localwhitelist"])
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def localallowlist(self, ctx: commands.Context):
        """
        Commands to manage the server specific allowlist.

        Warning: When the allowlist is in use, the bot will ignore commands from everyone not on the list in the server.

        Use `[p]localallowlist clear` to disable the allowlist
        """
        pass

    @localallowlist.command(name="add", require_var_positional=True)
    async def localallowlist_add(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Adds a user or role to the server allowlist.

        **Examples:**
            - `[p]localallowlist add @26 @Will` - Adds two users to the local allowlist.
            - `[p]localallowlist add 262626262626262626` - Allows a user by ID.
            - `[p]localallowlist add "Super Admins"` - Allows a role with a space in the name without mentioning.

        **Arguments:**
            - `<users_or_roles...>` - The users or roles to remove from the local allowlist.
        """
        names = [getattr(u_or_r, "name", u_or_r) for u_or_r in users_or_roles]
        uids = {getattr(u_or_r, "id", u_or_r) for u_or_r in users_or_roles}
        if not (ctx.guild.owner == ctx.author or await self.bot.is_owner(ctx.author)):
            current_whitelist = await self.bot._whiteblacklist_cache.get_whitelist(ctx.guild)
            theoretical_whitelist = current_whitelist.union(uids)
            ids = {i for i in (ctx.author.id, *(getattr(ctx.author, "_roles", [])))}
            if ids.isdisjoint(theoretical_whitelist):
                return await ctx.send(
                    _(
                        "I cannot allow you to do this, as it would "
                        "remove your ability to run commands, "
                        "please ensure to add yourself to the allowlist first."
                    )
                )
        await self.bot.add_to_allowlist_raw(uids, ctx.guild.id)

        if len(uids) > 1:
            await ctx.send(_("Users and/or roles have been added to the allowlist."))
        else:
            await ctx.send(_("User or role has been added to the allowlist."))

    @localallowlist.command(name="list")
    async def localallowlist_list(self, ctx: commands.Context):
        """
        Lists users and roles on the server allowlist.

        **Example:**
            - `[p]localallowlist list`
        """
        curr_list = await self.bot._whiteblacklist_cache.get_whitelist(ctx.guild)

        if not curr_list:
            await ctx.send("Server allowlist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Allowed users and/or roles:")
        else:
            msg = _("Allowed user or role:")
        for obj_id in curr_list:
            user_or_role = self.bot.get_user(obj_id) or ctx.guild.get_role(obj_id)
            if not user_or_role:
                user_or_role = _("Unknown or Deleted User/Role")
            msg += f"\n\t- {obj_id} ({user_or_role})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @localallowlist.command(name="remove", require_var_positional=True)
    async def localallowlist_remove(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Removes user or role from the allowlist.

        The local allowlist will be disabled if all users are removed.

        **Examples:**
            - `[p]localallowlist remove @26 @Will` - Removes two users from the local allowlist.
            - `[p]localallowlist remove 262626262626262626` - Removes a user by ID.
            - `[p]localallowlist remove "Super Admins"` - Removes a role with a space in the name without mentioning.

        **Arguments:**
            - `<users_or_roles...>` - The users or roles to remove from the local allowlist.
        """
        names = [getattr(u_or_r, "name", u_or_r) for u_or_r in users_or_roles]
        uids = {getattr(u_or_r, "id", u_or_r) for u_or_r in users_or_roles}
        if not (ctx.guild.owner == ctx.author or await self.bot.is_owner(ctx.author)):
            current_whitelist = await self.bot._whiteblacklist_cache.get_whitelist(ctx.guild)
            theoretical_whitelist = current_whitelist - uids
            ids = {i for i in (ctx.author.id, *(getattr(ctx.author, "_roles", [])))}
            if theoretical_whitelist and ids.isdisjoint(theoretical_whitelist):
                return await ctx.send(
                    _(
                        "I cannot allow you to do this, as it would "
                        "remove your ability to run commands."
                    )
                )
        await self.bot.remove_from_allowlist_raw(uids, ctx.guild.id)

        if len(uids) > 1:
            await ctx.send(_("Users and/or roles have been removed from the server allowlist."))
        else:
            await ctx.send(_("User or role has been removed from the server allowlist."))

    @localallowlist.command(name="clear")
    async def localallowlist_clear(self, ctx: commands.Context):
        """
        Clears the allowlist.

        This disables the local allowlist and clears all entires.

        **Example:**
            - `[p]localallowlist clear`
        """
        await self.bot._whiteblacklist_cache.clear_whitelist(ctx.guild)
        await ctx.send(_("Server allowlist has been cleared."))

    @commands.group(aliases=["localblacklist"])
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def localblocklist(self, ctx: commands.Context):
        """
        Commands to manage the server specific blocklist.

        Use `[p]localblocklist clear` to disable the blocklist
        """
        pass

    @localblocklist.command(name="add", require_var_positional=True)
    async def localblocklist_add(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Adds a user or role to the local blocklist.

        **Examples:**
            - `[p]localblocklist add @26 @Will` - Adds two users to the local blocklist.
            - `[p]localblocklist add 262626262626262626` - Blocks a user by ID.
            - `[p]localblocklist add "Bad Apples"` - Blocks a role with a space in the name without mentioning.

        **Arguments:**
            - `<users_or_roles...>` - The users or roles to add to the local blocklist.
        """
        for user_or_role in users_or_roles:
            uid = discord.Object(id=getattr(user_or_role, "id", user_or_role))
            if uid.id == ctx.author.id:
                await ctx.send(_("You cannot add yourself to the blocklist!"))
                return
            if uid.id == ctx.guild.owner_id and not await ctx.bot.is_owner(ctx.author):
                await ctx.send(_("You cannot add the guild owner to the blocklist!"))
                return
            if await ctx.bot.is_owner(uid):
                await ctx.send(_("You cannot add a bot owner to the blocklist!"))
                return
        names = [getattr(u_or_r, "name", u_or_r) for u_or_r in users_or_roles]
        uids = {getattr(u_or_r, "id", u_or_r) for u_or_r in users_or_roles}
        await self.bot.add_to_blocklist_raw(uids, ctx.guild.id)

        if len(uids) > 1:
            await ctx.send(_("Users and/or roles have been added from the server blocklist."))
        else:
            await ctx.send(_("User or role has been added from the server blocklist."))

    @localblocklist.command(name="list")
    async def localblocklist_list(self, ctx: commands.Context):
        """
        Lists users and roles on the server blocklist.

        **Example:**
            - `[p]localblocklist list`
        """
        curr_list = await self.bot._whiteblacklist_cache.get_blacklist(ctx.guild)

        if not curr_list:
            await ctx.send("Server blocklist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Blocked users and/or roles:")
        else:
            msg = _("Blocked user or role:")
        for obj_id in curr_list:
            user_or_role = self.bot.get_user(obj_id) or ctx.guild.get_role(obj_id)
            if not user_or_role:
                user_or_role = _("Unknown or Deleted User/Role")
            msg += f"\n\t- {obj_id} ({user_or_role})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @localblocklist.command(name="remove", require_var_positional=True)
    async def localblocklist_remove(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Removes user or role from blocklist.

        **Examples:**
            - `[p]localblocklist remove @26 @Will` - Removes two users from the local blocklist.
            - `[p]localblocklist remove 262626262626262626` - Unblocks a user by ID.
            - `[p]localblocklist remove "Bad Apples"` - Unblocks a role with a space in the name without mentioning.

        **Arguments:**
            - `<users_or_roles...>` - The users or roles to remove from the local blocklist.
        """
        names = [getattr(u_or_r, "name", u_or_r) for u_or_r in users_or_roles]
        uids = {getattr(u_or_r, "id", u_or_r) for u_or_r in users_or_roles}
        await self.bot.remove_from_blocklist_raw(uids, ctx.guild.id)

        if len(uids) > 1:
            await ctx.send(_("Users and/or roles have been removed from the server blocklist."))
        else:
            await ctx.send(_("User or role has been removed from the server blocklist."))

    @localblocklist.command(name="clear")
    async def localblocklist_clear(self, ctx: commands.Context):
        """
        Clears the server blocklist.

        This disabled the server blocklist and clears all entries.

        **Example:**
            - `[p]blocklist clear`
        """
        await self.bot._whiteblacklist_cache.clear_blacklist(ctx.guild)
        await ctx.send(_("Server blocklist has been cleared."))

    @checks.guildowner_or_permissions(administrator=True)
    @commands.group(name="command")
    async def command_manager(self, ctx: commands.Context):
        """Commands to enable and disable commands and cogs."""
        pass

    @checks.is_owner()
    @command_manager.command(name="defaultdisablecog")
    async def command_default_disable_cog(self, ctx: commands.Context, *, cogname: str):
        """Set the default state for a cog as disabled.

        This will disable the cog for all servers by default.
        To override it, use `[p]command enablecog` on the servers you want to allow usage.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
            - `[p]command defaultdisablecog Economy`
            - `[p]command defaultdisablecog ModLog`

        **Arguments:**
            - `<cogname>` - The name of the cog to make disabled by default. Must be title-case.
        """
        cog = self.bot.get_cog(cogname)
        if not cog:
            return await ctx.send(_("Cog with the given name doesn't exist."))
        if isinstance(cog, commands.commands._RuleDropper):
            return await ctx.send(_("You can't disable this cog by default."))
        await self.bot._disabled_cog_cache.default_disable(cogname)
        await ctx.send(_("{cogname} has been set as disabled by default.").format(cogname=cogname))

    @checks.is_owner()
    @command_manager.command(name="defaultenablecog")
    async def command_default_enable_cog(self, ctx: commands.Context, *, cogname: str):
        """Set the default state for a cog as enabled.

        This will re-enable the cog for all servers by default.
        To override it, use `[p]command disablecog` on the servers you want to disallow usage.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
            - `[p]command defaultenablecog Economy`
            - `[p]command defaultenablecog ModLog`

        **Arguments:**
            - `<cogname>` - The name of the cog to make enabled by default. Must be title-case.
        """
        cog = self.bot.get_cog(cogname)
        if not cog:
            return await ctx.send(_("Cog with the given name doesn't exist."))
        await self.bot._disabled_cog_cache.default_enable(cogname)
        await ctx.send(_("{cogname} has been set as enabled by default.").format(cogname=cogname))

    @commands.guild_only()
    @command_manager.command(name="disablecog")
    async def command_disable_cog(self, ctx: commands.Context, *, cogname: str):
        """Disable a cog in this server.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
            - `[p]command disablecog Economy`
            - `[p]command disablecog ModLog`

        **Arguments:**
            - `<cogname>` - The name of the cog to disable on this server. Must be title-case.
        """
        cog = self.bot.get_cog(cogname)
        if not cog:
            return await ctx.send(_("Cog with the given name doesn't exist."))
        if isinstance(cog, commands.commands._RuleDropper):
            return await ctx.send(_("You can't disable this cog as you would lock yourself out."))
        if await self.bot._disabled_cog_cache.disable_cog_in_guild(cogname, ctx.guild.id):
            await ctx.send(_("{cogname} has been disabled in this guild.").format(cogname=cogname))
        else:
            await ctx.send(
                _("{cogname} was already disabled (nothing to do).").format(cogname=cogname)
            )

    @commands.guild_only()
    @command_manager.command(name="enablecog")
    async def command_enable_cog(self, ctx: commands.Context, *, cogname: str):
        """Enable a cog in this server.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
            - `[p]command enablecog Economy`
            - `[p]command enablecog ModLog`

        **Arguments:**
            - `<cogname>` - The name of the cog to enable on this server. Must be title-case.
        """
        if await self.bot._disabled_cog_cache.enable_cog_in_guild(cogname, ctx.guild.id):
            await ctx.send(_("{cogname} has been enabled in this guild.").format(cogname=cogname))
        else:
            # putting this here allows enabling a cog that isn't loaded but was disabled.
            cog = self.bot.get_cog(cogname)
            if not cog:
                return await ctx.send(_("Cog with the given name doesn't exist."))

            await ctx.send(
                _("{cogname} was not disabled (nothing to do).").format(cogname=cogname)
            )

    @commands.guild_only()
    @command_manager.command(name="listdisabledcogs")
    async def command_list_disabled_cogs(self, ctx: commands.Context):
        """List the cogs which are disabled in this server.

        **Example:**
            - `[p]command listdisabledcogs`
        """
        disabled = [
            cog.qualified_name
            for cog in self.bot.cogs.values()
            if await self.bot._disabled_cog_cache.cog_disabled_in_guild(
                cog.qualified_name, ctx.guild.id
            )
        ]
        if disabled:
            output = _("The following cogs are disabled in this guild:\n")
            output += humanize_list(disabled)

            for page in pagify(output):
                await ctx.send(page)
        else:
            await ctx.send(_("There are no disabled cogs in this guild."))

    @command_manager.group(name="listdisabled", invoke_without_command=True)
    async def list_disabled(self, ctx: commands.Context):
        """
        List disabled commands.

        If you're the bot owner, this will show global disabled commands by default.
        Otherwise, this will show disabled commands on the current server.

        **Example:**
            - `[p]command listdisabled`
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.list_disabled_global)
        else:
            await ctx.invoke(self.list_disabled_guild)

    @list_disabled.command(name="global")
    async def list_disabled_global(self, ctx: commands.Context):
        """List disabled commands globally.

        **Example:**
            - `[p]command listdisabled global`
        """
        disabled_list = await self.bot._config.disabled_commands()
        if not disabled_list:
            return await ctx.send(_("There aren't any globally disabled commands."))

        if len(disabled_list) > 1:
            header = _("{} commands are disabled globally.\n").format(
                humanize_number(len(disabled_list))
            )
        else:
            header = _("1 command is disabled globally.\n")
        paged = [box(x) for x in pagify(humanize_list(disabled_list), page_length=1000)]
        paged[0] = header + paged[0]
        await ctx.send_interactive(paged)

    @commands.guild_only()
    @list_disabled.command(name="guild")
    async def list_disabled_guild(self, ctx: commands.Context):
        """List disabled commands in this server.

        **Example:**
            - `[p]command listdisabled guild`
        """
        disabled_list = await self.bot._config.guild(ctx.guild).disabled_commands()
        if not disabled_list:
            return await ctx.send(_("There aren't any disabled commands in {}.").format(ctx.guild))

        if len(disabled_list) > 1:
            header = _("{} commands are disabled in {}.\n").format(
                humanize_number(len(disabled_list)), ctx.guild
            )
        else:
            header = _("1 command is disabled in {}.\n").format(ctx.guild)
        paged = [box(x) for x in pagify(humanize_list(disabled_list), page_length=1000)]
        paged[0] = header + paged[0]
        await ctx.send_interactive(paged)

    @command_manager.group(name="disable", invoke_without_command=True)
    async def command_disable(self, ctx: commands.Context, *, command: str):
        """
        Disable a command.

        If you're the bot owner, this will disable commands globally by default.
        Otherwise, this will disable commands on the current server.

        **Examples:**
            - `[p]command disable userinfo` - Disables the `userinfo` command in the Mod cog.
            - `[p]command disable urban` - Disables the `urban` command in the General cog.

        **Arguments:**
            - `<command>` - The command to disable.
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_disable_global, command=command)
        else:
            await ctx.invoke(self.command_disable_guild, command=command)

    @checks.is_owner()
    @command_disable.command(name="global")
    async def command_disable_global(self, ctx: commands.Context, *, command: str):
        """
        Disable a command globally.

        **Examples:**
            - `[p]command disable global userinfo` - Disables the `userinfo` command in the Mod cog.
            - `[p]command disable global urban` - Disables the `urban` command in the General cog.

        **Arguments:**
            - `<command>` - The command to disable globally.
        """
        command_obj: Optional[commands.Command] = ctx.bot.get_command(command)
        if command_obj is None:
            await ctx.send(
                _("I couldn't find that command. Please note that it is case sensitive.")
            )
            return

        if self.command_manager in command_obj.parents or self.command_manager == command_obj:
            await ctx.send(
                _("The command to disable cannot be `command` or any of its subcommands.")
            )
            return

        if isinstance(command_obj, commands.commands._RuleDropper):
            await ctx.send(
                _("This command is designated as being always available and cannot be disabled.")
            )
            return

        async with ctx.bot._config.disabled_commands() as disabled_commands:
            if command not in disabled_commands:
                disabled_commands.append(command_obj.qualified_name)

        if not command_obj.enabled:
            await ctx.send(_("That command is already disabled globally."))
            return
        command_obj.enabled = False

        await ctx.tick()

    @commands.guild_only()
    @command_disable.command(name="server", aliases=["guild"])
    async def command_disable_guild(self, ctx: commands.Context, *, command: str):
        """
        Disable a command in this server only.

                **Examples:**
                    - `[p]command disable server userinfo` - Disables the `userinfo` command in the Mod cog.
                    - `[p]command disable server urban` - Disables the `urban` command in the General cog.

                **Arguments:**
                    - `<command>` - The command to disable for the current server.
        """
        command_obj: Optional[commands.Command] = ctx.bot.get_command(command)
        if command_obj is None:
            await ctx.send(
                _("I couldn't find that command. Please note that it is case sensitive.")
            )
            return

        if self.command_manager in command_obj.parents or self.command_manager == command_obj:
            await ctx.send(
                _("The command to disable cannot be `command` or any of its subcommands.")
            )
            return

        if isinstance(command_obj, commands.commands._RuleDropper):
            await ctx.send(
                _("This command is designated as being always available and cannot be disabled.")
            )
            return

        if command_obj.requires.privilege_level > await PrivilegeLevel.from_ctx(ctx):
            await ctx.send(_("You are not allowed to disable that command."))
            return

        async with ctx.bot._config.guild(ctx.guild).disabled_commands() as disabled_commands:
            if command not in disabled_commands:
                disabled_commands.append(command_obj.qualified_name)

        done = command_obj.disable_in(ctx.guild)

        if not done:
            await ctx.send(_("That command is already disabled in this server."))
        else:
            await ctx.tick()

    @command_manager.group(name="enable", invoke_without_command=True)
    async def command_enable(self, ctx: commands.Context, *, command: str):
        """Enable a command.

        If you're the bot owner, this will try to enable a globally disabled command by default.
        Otherwise, this will try to enable a command disabled on the current server.

        **Examples:**
            - `[p]command enable userinfo` - Enables the `userinfo` command in the Mod cog.
            - `[p]command enable urban` - Enables the `urban` command in the General cog.

        **Arguments:**
            - `<command>` - The command to enable.
        """
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_enable_global, command=command)
        else:
            await ctx.invoke(self.command_enable_guild, command=command)

    @commands.is_owner()
    @command_enable.command(name="global")
    async def command_enable_global(self, ctx: commands.Context, *, command: str):
        """
                Enable a command globally.

        **Examples:**
            - `[p]command enable global userinfo` - Enables the `userinfo` command in the Mod cog.
            - `[p]command enable global urban` - Enables the `urban` command in the General cog.

        **Arguments:**
            - `<command>` - The command to enable globally.
        """
        command_obj: Optional[commands.Command] = ctx.bot.get_command(command)
        if command_obj is None:
            await ctx.send(
                _("I couldn't find that command. Please note that it is case sensitive.")
            )
            return

        async with ctx.bot._config.disabled_commands() as disabled_commands:
            with contextlib.suppress(ValueError):
                disabled_commands.remove(command_obj.qualified_name)

        if command_obj.enabled:
            await ctx.send(_("That command is already enabled globally."))
            return

        command_obj.enabled = True
        await ctx.tick()

    @commands.guild_only()
    @command_enable.command(name="server", aliases=["guild"])
    async def command_enable_guild(self, ctx: commands.Context, *, command: str):
        """
            Enable a command in this server.

        **Examples:**
            - `[p]command enable server userinfo` - Enables the `userinfo` command in the Mod cog.
            - `[p]command enable server urban` - Enables the `urban` command in the General cog.

        **Arguments:**
            - `<command>` - The command to enable for the current server.
        """
        command_obj: Optional[commands.Command] = ctx.bot.get_command(command)
        if command_obj is None:
            await ctx.send(
                _("I couldn't find that command. Please note that it is case sensitive.")
            )
            return

        if command_obj.requires.privilege_level > await PrivilegeLevel.from_ctx(ctx):
            await ctx.send(_("You are not allowed to enable that command."))
            return

        async with ctx.bot._config.guild(ctx.guild).disabled_commands() as disabled_commands:
            with contextlib.suppress(ValueError):
                disabled_commands.remove(command_obj.qualified_name)

        done = command_obj.enable_in(ctx.guild)

        if not done:
            await ctx.send(_("That command is already enabled in this server."))
        else:
            await ctx.tick()

    @checks.is_owner()
    @command_manager.command(name="disabledmsg")
    async def command_disabledmsg(self, ctx: commands.Context, *, message: str = ""):
        """Set the bot's response to disabled commands.

        Leave blank to send nothing.

        To include the command name in the message, include the `{command}` placeholder.

        **Examples:**
            - `[p]command disabledmsg This command is disabled`
            - `[p]command disabledmsg {command} is disabled`
            - `[p]command disabledmsg` - Sends nothing when a disabled command is attempted.

        **Arguments:**
            - `[message]` - The message to send when a disabled command is attempted.
        """
        await ctx.bot._config.disabled_command_msg.set(message)
        await ctx.tick()

    @commands.guild_only()
    @checks.guildowner_or_permissions(manage_guild=True)
    @commands.group(name="autoimmune")
    async def autoimmune_group(self, ctx: commands.Context):
        """
        Commands to manage server settings for immunity from automated actions.

        This includes duplicate message deletion and mention spam from the Mod cog, and filters from the Filter cog.
        """
        pass

    @autoimmune_group.command(name="list")
    async def autoimmune_list(self, ctx: commands.Context):
        """
        Gets the current members and roles configured for automatic moderation action immunity.

        **Example:**
            - `[p]autoimmune list`
        """
        ai_ids = await ctx.bot._config.guild(ctx.guild).autoimmune_ids()

        roles = {r.name for r in ctx.guild.roles if r.id in ai_ids}
        members = {str(m) for m in ctx.guild.members if m.id in ai_ids}

        output = ""
        if roles:
            output += _("Roles immune from automated moderation actions:\n")
            output += ", ".join(roles)
        if members:
            if roles:
                output += "\n"
            output += _("Members immune from automated moderation actions:\n")
            output += ", ".join(members)

        if not output:
            output = _("No immunity settings here.")

        for page in pagify(output):
            await ctx.send(page)

    @autoimmune_group.command(name="add")
    async def autoimmune_add(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Makes a user or role immune from automated moderation actions.

        **Examples:**
            - `[p]autoimmune add @TwentySix` - Adds a user.
            - `[p]autoimmune add @Mods` - Adds a role.

        **Arguments:**
            - `<user_or_role>` - The user or role to add immunity to.
        """
        async with ctx.bot._config.guild(ctx.guild).autoimmune_ids() as ai_ids:
            if user_or_role.id in ai_ids:
                return await ctx.send(_("Already added."))
            ai_ids.append(user_or_role.id)
        await ctx.tick()

    @autoimmune_group.command(name="remove")
    async def autoimmune_remove(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Makes a user or role immune from automated moderation actions.

        **Examples:**
            - `[p]autoimmune remove @TwentySix` - Removes a user.
            - `[p]autoimmune remove @Mods` - Removes a role.

        **Arguments:**
            - `<user_or_role>` - The user or role to remove immunity from.
        """
        async with ctx.bot._config.guild(ctx.guild).autoimmune_ids() as ai_ids:
            if user_or_role.id not in ai_ids:
                return await ctx.send(_("Not in list."))
            ai_ids.remove(user_or_role.id)
        await ctx.tick()

    @autoimmune_group.command(name="isimmune")
    async def autoimmune_checkimmune(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Checks if a user or role would be considered immune from automated actions.

        **Examples:**
            - `[p]autoimmune isimmune @TwentySix`
            - `[p]autoimmune isimmune @Mods`

        **Arguments:**
            - `<user_or_role>` - The user or role to check the immunity of.
        """

        if await ctx.bot.is_automod_immune(user_or_role):
            await ctx.send(_("They are immune."))
        else:
            await ctx.send(_("They are not immune."))

    @checks.is_owner()
    @_set.group()
    async def ownernotifications(self, ctx: commands.Context):
        """
        Commands for configuring owner notifications.

        Owner notifications include usage of `[p]contact` and available Red updates.
        """
        pass

    @ownernotifications.command()
    async def optin(self, ctx: commands.Context):
        """
        Opt-in on receiving owner notifications.

        This is the default state.

        Note: This will only resume sending owner notifications to your DMs.
            Additional owners and destinations will not be affected.

        **Example:**
            - `[p]ownernotifications optin`
        """
        async with ctx.bot._config.owner_opt_out_list() as opt_outs:
            if ctx.author.id in opt_outs:
                opt_outs.remove(ctx.author.id)

        await ctx.tick()

    @ownernotifications.command()
    async def optout(self, ctx: commands.Context):
        """
        Opt-out of receiving owner notifications.

        Note: This will only stop sending owner notifications to your DMs.
            Additional owners and destinations will still receive notifications.

        **Example:**
            - `[p]ownernotifications optout`
        """
        async with ctx.bot._config.owner_opt_out_list() as opt_outs:
            if ctx.author.id not in opt_outs:
                opt_outs.append(ctx.author.id)

        await ctx.tick()

    @ownernotifications.command()
    async def adddestination(
        self, ctx: commands.Context, *, channel: Union[discord.TextChannel, int]
    ):
        """
        Adds a destination text channel to receive owner notifications.

        **Examples:**
            - `[p]ownernotifications adddestination #owner-notifications`
            - `[p]ownernotifications adddestination 168091848718417920` - Accepts channel IDs.

        **Arguments:**
            - `<channel>` - The channel to send owner notifications to.
        """

        try:
            channel_id = channel.id
        except AttributeError:
            channel_id = channel

        async with ctx.bot._config.extra_owner_destinations() as extras:
            if channel_id not in extras:
                extras.append(channel_id)

        await ctx.tick()

    @ownernotifications.command(aliases=["remdestination", "deletedestination", "deldestination"])
    async def removedestination(
        self, ctx: commands.Context, *, channel: Union[discord.TextChannel, int]
    ):
        """
        Removes a destination text channel from receiving owner notifications.

        **Examples:**
            - `[p]ownernotifications removedestination #owner-notifications`
            - `[p]ownernotifications deletedestination 168091848718417920` - Accepts channel IDs.

        **Arguments:**
            - `<channel>` - The channel to stop sending owner notifications to.
        """

        try:
            channel_id = channel.id
        except AttributeError:
            channel_id = channel

        async with ctx.bot._config.extra_owner_destinations() as extras:
            if channel_id in extras:
                extras.remove(channel_id)

        await ctx.tick()

    @ownernotifications.command()
    async def listdestinations(self, ctx: commands.Context):
        """
        Lists the configured extra destinations for owner notifications.

        **Example:**
            - `[p]ownernotifications listdestinations`
        """

        channel_ids = await ctx.bot._config.extra_owner_destinations()

        if not channel_ids:
            await ctx.send(_("There are no extra channels being sent to."))
            return

        data = []

        for channel_id in channel_ids:
            channel = ctx.bot.get_channel(channel_id)
            if channel:
                # This includes the channel name in case the user can't see the channel.
                data.append(f"{channel.mention} {channel} ({channel.id})")
            else:
                data.append(_("Unknown channel with id: {id}").format(id=channel_id))

        output = "\n".join(data)
        for page in pagify(output):
            await ctx.send(page)

    # RPC handlers
    async def rpc_load(self, request):
        cog_name = request.params[0]

        spec = await self.bot._cog_mgr.find_cog(cog_name)
        if spec is None:
            raise LookupError("No such cog found.")

        self._cleanup_and_refresh_modules(spec.name)

        await self.bot.load_extension(spec)

    async def rpc_unload(self, request):
        cog_name = request.params[0]

        self.bot.unload_extension(cog_name)

    async def rpc_reload(self, request):
        await self.rpc_unload(request)
        await self.rpc_load(request)

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context):
        """
        Commands to add servers or channels to the ignore list.

        The ignore list will prevent the bot from responding to commands in the configured locations.

        Note: Owners and Admins override the ignore list.
        """

    @ignore.command(name="list")
    async def ignore_list(self, ctx: commands.Context):
        """
        List the currently ignored servers and channels.

        **Example:**
            - `[p]ignore list`
        """
        for page in pagify(await self.count_ignored(ctx)):
            await ctx.maybe_send_embed(page)

    @ignore.command(name="channel")
    async def ignore_channel(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """
        Ignore commands in the channel or category.

        Defaults to the current channel.

        Note: Owners, Admins, and those with Manage Channel permissions override ignored channels.

        **Examples:**
            - `[p]ignore channel #general` - Ignores commands in the #general channel.
            - `[p]ignore channel` - Ignores commands in the current channel.
            - `[p]ignore channel "General Channels"` - Use quotes for categories with spaces.
            - `[p]ignore channel 356236713347252226` - Also accepts IDs.

        **Arguments:**
            - `<channel>` - The channel to ignore. Can be a category channel.
        """
        if not channel:
            channel = ctx.channel
        if not await self.bot._ignored_cache.get_ignored_channel(channel):
            await self.bot._ignored_cache.set_ignored_channel(channel, True)
            await ctx.send(_("Channel added to ignore list."))
        else:
            await ctx.send(_("Channel already in ignore list."))

    @ignore.command(name="server", aliases=["guild"])
    @checks.admin_or_permissions(manage_guild=True)
    async def ignore_guild(self, ctx: commands.Context):
        """
        Ignore commands in this server.

        Note: Owners, Admins, and those with Manage Server permissions override ignored servers.

        **Example:**
            - `[p]ignore server` - Ignores the current server
        """
        guild = ctx.guild
        if not await self.bot._ignored_cache.get_ignored_guild(guild):
            await self.bot._ignored_cache.set_ignored_guild(guild, True)
            await ctx.send(_("This server has been added to the ignore list."))
        else:
            await ctx.send(_("This server is already being ignored."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx: commands.Context):
        """Commands to remove servers or channels from the ignore list."""

    @unignore.command(name="channel")
    async def unignore_channel(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """
        Remove a channel or category from the ignore list.

        Defaults to the current channel.

        **Examples:**
            - `[p]unignore channel #general` - Unignores commands in the #general channel.
            - `[p]unignore channel` - Unignores commands in the current channel.
            - `[p]unignore channel "General Channels"` - Use quotes for categories with spaces.
            - `[p]unignore channel 356236713347252226` - Also accepts IDs. Use this method to unignore categories.

        **Arguments:**
            - `<channel>` - The channel to unignore. This can be a category channel.
        """
        if not channel:
            channel = ctx.channel

        if await self.bot._ignored_cache.get_ignored_channel(channel):
            await self.bot._ignored_cache.set_ignored_channel(channel, False)
            await ctx.send(_("Channel removed from ignore list."))
        else:
            await ctx.send(_("That channel is not in the ignore list."))

    @unignore.command(name="server", aliases=["guild"])
    @checks.admin_or_permissions(manage_guild=True)
    async def unignore_guild(self, ctx: commands.Context):
        """
        Remove this server from the ignore list.

        **Example:**
            - `[p]unignore server` - Stops ignoring the current server
        """
        guild = ctx.message.guild
        if await self.bot._ignored_cache.get_ignored_guild(guild):
            await self.bot._ignored_cache.set_ignored_guild(guild, False)
            await ctx.send(_("This server has been removed from the ignore list."))
        else:
            await ctx.send(_("This server is not in the ignore list."))

    async def count_ignored(self, ctx: commands.Context):
        category_channels: List[discord.CategoryChannel] = []
        text_channels: List[discord.TextChannel] = []
        if await self.bot._ignored_cache.get_ignored_guild(ctx.guild):
            return _("This server is currently being ignored.")
        for channel in ctx.guild.text_channels:
            if channel.category and channel.category not in category_channels:
                if await self.bot._ignored_cache.get_ignored_channel(channel.category):
                    category_channels.append(channel.category)
            if await self.bot._ignored_cache.get_ignored_channel(channel, check_category=False):
                text_channels.append(channel)

        cat_str = (
            humanize_list([c.name for c in category_channels]) if category_channels else "None"
        )
        chan_str = humanize_list([c.mention for c in text_channels]) if text_channels else "None"
        msg = _("Currently ignored categories: {categories}\nChannels: {channels}").format(
            categories=cat_str, channels=chan_str
        )
        return msg

    @commands.command(
        cls=commands.commands._IsTrueBotOwner,
        name="su",
    )
    async def su(self, ctx: commands.Context):
        """Enable your bot owner privileges.

        SU permission is auto removed after interval set with `[p]set sutimeout` (Default to 15 minutes).
        """
        if ctx.author.id not in self.bot.owner_ids:
            self.bot._elevated_owner_ids |= {ctx.author.id}
            await ctx.send(_("Your bot owner privileges have been enabled."))
            if ctx.author.id in self.bot._owner_sudo_tasks:
                self.bot._owner_sudo_tasks[ctx.author.id].cancel()
                del self.bot._owner_sudo_tasks[ctx.author.id]
            self.bot._owner_sudo_tasks[ctx.author.id] = asyncio.create_task(
                timed_unsu(ctx.author.id, self.bot)
            )
            return
        await ctx.send(_("Your bot owner privileges are already enabled."))

    @commands.command(
        cls=commands.commands._IsTrueBotOwner,
        name="unsu",
    )
    async def unsu(self, ctx: commands.Context):
        """Disable your bot owner privileges."""
        if ctx.author.id in self.bot.owner_ids:
            self.bot._elevated_owner_ids -= {ctx.author.id}
            await ctx.send(_("Your bot owner privileges have been disabled."))
            return
        await ctx.send(_("Your bot owner privileges are not currently enabled."))

    @commands.command(
        cls=commands.commands._IsTrueBotOwner,
        name="sudo",
    )
    async def sudo(self, ctx: commands.Context, *, command: str):
        """Runs the specified command with bot owner permissions

        The prefix must not be entered.
        """
        ids = self.bot._elevated_owner_ids.union({ctx.author.id})
        self.bot._sudo_ctx_var.set(ids)
        msg = copy(ctx.message)
        msg.content = ctx.prefix + command
        ctx.bot.dispatch("message", msg)

    @_set.command()
    @is_sudo_enabled()
    @checks.is_owner()
    async def sutimeout(
        self,
        ctx: commands.Context,
        *,
        interval: commands.TimedeltaConverter(
            minimum=datetime.timedelta(minutes=1),
            maximum=datetime.timedelta(days=1),
            default_unit="minutes",
        ) = datetime.timedelta(minutes=15),
    ):
        """
        Set the interval for SU permissions to auto expire.
        """
        await self.bot._config.sudotime.set(interval.total_seconds())
        await ctx.send(
            _("SU timer will expire after: {}.").format(humanize_timedelta(timedelta=interval))
        )

    # Removing this command from forks is a violation of the GPLv3 under which it is licensed.
    # Otherwise interfering with the ability for this command to be accessible is also a violation.
    @commands.cooldown(1, 180, lambda msg: (msg.channel.id, msg.author.id))
    @commands.command(
        cls=commands.commands._AlwaysAvailableCommand,
        name="licenseinfo",
        aliases=["licenceinfo"],
        i18n=_,
    )
    async def license_info_command(self, ctx):
        """
        Get info about Red's licenses.
        """

        message = (
            "This bot is an instance of Red-DiscordBot (hereinafter referred to as Red).\n"
            "Red is a free and open source application made available to the public and "
            "licensed under the GNU GPLv3. The full text of this license is available to you at "
            "<https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/LICENSE>."
        )
        await ctx.send(message)
        # We need a link which contains a thank you to other projects which we use at some point.
