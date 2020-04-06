import asyncio
import contextlib
import datetime
import importlib
import itertools
import logging
import os
import re
import sys
import platform
import getpass
import pip
import traceback
from collections import namedtuple
from pathlib import Path
from random import SystemRandom
from string import ascii_letters, digits
from typing import TYPE_CHECKING, Union, Tuple, List, Optional, Iterable, Sequence, Dict, Set

import aiohttp
import discord
import pkg_resources
from babel import Locale as BabelLocale, UnknownLocaleError

from . import (
    __version__,
    version_info as red_version_info,
    VersionInfo,
    checks,
    commands,
    drivers,
    errors,
    i18n,
    config,
)
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
        self, cog_names: Iterable[str]
    ) -> Tuple[List[str], List[str], List[str], List[str], List[Tuple[str, str]], Set[str]]:
        """
        Loads cogs by name.
        Parameters
        ----------
        cog_names : list of str

        Returns
        -------
        tuple
            4-tuple of loaded, failed, not found and already loaded cogs.
        """
        failed_packages = []
        loaded_packages = []
        notfound_packages = []
        alreadyloaded_packages = []
        failed_with_reason_packages = []
        repos_with_shared_libs = set()

        bot = self.bot

        cogspecs = []

        for name in cog_names:
            try:
                spec = await bot._cog_mgr.find_cog(name)
                if spec:
                    cogspecs.append((spec, name))
                else:
                    notfound_packages.append(name)
            except Exception as e:
                log.exception("Package import failed", exc_info=e)

                exception_log = "Exception during import of cog\n"
                exception_log += "".join(traceback.format_exception(type(e), e, e.__traceback__))
                bot._last_exception = exception_log
                failed_packages.append(name)

        for spec, name in cogspecs:
            try:
                self._cleanup_and_refresh_modules(spec.name)
                await bot.load_extension(spec)
            except errors.PackageAlreadyLoaded:
                alreadyloaded_packages.append(name)
            except errors.CogLoadError as e:
                failed_with_reason_packages.append((name, str(e)))
            except Exception as e:
                log.exception("Package loading failed", exc_info=e)

                exception_log = "Exception during loading of cog\n"
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
            notfound_packages,
            alreadyloaded_packages,
            failed_with_reason_packages,
            repos_with_shared_libs,
        )

    @staticmethod
    def _cleanup_and_refresh_modules(module_name: str) -> None:
        """Interally reloads modules so that changes are detected"""
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

    async def _unload(self, cog_names: Iterable[str]) -> Tuple[List[str], List[str]]:
        """
        Unloads cogs with the given names.

        Parameters
        ----------
        cog_names : list of str

        Returns
        -------
        tuple
            2 element tuple of successful unloads and failed unloads.
        """
        failed_packages = []
        unloaded_packages = []

        bot = self.bot

        for name in cog_names:
            if name in bot.extensions:
                bot.unload_extension(name)
                await bot.remove_loaded_package(name)
                unloaded_packages.append(name)
            else:
                failed_packages.append(name)

        return unloaded_packages, failed_packages

    async def _reload(
        self, cog_names: Sequence[str]
    ) -> Tuple[List[str], List[str], List[str], List[str], List[Tuple[str, str]], Set[str]]:
        await self._unload(cog_names)

        (
            loaded,
            load_failed,
            not_found,
            already_loaded,
            load_failed_with_reason,
            repos_with_shared_libs,
        ) = await self._load(cog_names)

        return (
            loaded,
            load_failed,
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
            await self.bot._prefix_cache.set_prefixes(guild=None, prefixes=prefixes)
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
class Core(commands.Cog, CoreLogic):
    """Commands related to core functions"""

    @commands.command(hidden=True)
    async def ping(self, ctx: commands.Context):
        """Pong."""
        await ctx.send("Pong.")

    @commands.command()
    async def info(self, ctx: commands.Context):
        """Shows info about Red"""
        author_repo = "https://github.com/Twentysix26"
        org_repo = "https://github.com/Cog-Creators"
        red_repo = org_repo + "/Red-DiscordBot"
        red_pypi = "https://pypi.org/project/Red-DiscordBot"
        red_pypi_json = "https://pypi.org/pypi/Red-DiscordBot/json"
        support_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days
        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        python_version = "[{}.{}.{}]({})".format(*sys.version_info[:3], python_url)
        red_version = "[{}]({})".format(__version__, red_pypi)
        app_info = await self.bot.application_info()
        if app_info.team:
            owner = app_info.team.name
        else:
            owner = app_info.owner
        custom_info = await self.bot._config.custom_info()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(red_pypi_json) as r:
                    data = await r.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            outdated = None
        else:
            outdated = VersionInfo.from_str(data["info"]["version"]) > red_version_info
        about = _(
            "This bot is an instance of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and [improved by many]({}).\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
            "(c) Cog Creators"
        ).format(red_repo, author_repo, org_repo, support_server_url)

        embed = discord.Embed(color=(await ctx.embed_colour()))
        embed.add_field(name=_("Instance owned by"), value=str(owner))
        embed.add_field(name="Python", value=python_version)
        embed.add_field(name="discord.py", value=dpy_version)
        embed.add_field(name=_("Red version"), value=red_version)
        if outdated is True:
            outdated_value = _("Yes, {version} is available").format(
                version=data["info"]["version"]
            )
        elif outdated is None:
            outdated_value = _("Checking for updates failed.")
        else:
            outdated_value = _("No")
        embed.add_field(name=_("Outdated"), value=outdated_value)
        if custom_info:
            embed.add_field(name=_("About this instance"), value=custom_info, inline=False)
        embed.add_field(name=_("About Red"), value=about, inline=False)

        embed.set_footer(
            text=_("Bringing joy since 02 Jan 2016 (over {} days ago!)").format(days_since)
        )
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            await ctx.send(_("I need the `Embed links` permission to send this"))

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows [botname]'s uptime"""
        since = ctx.bot.uptime.strftime("%Y-%m-%d %H:%M:%S")
        delta = datetime.datetime.utcnow() - self.bot.uptime
        uptime_str = humanize_timedelta(timedelta=delta) or _("Less than one second")
        await ctx.send(
            _("Been up for: **{time_quantity}** (since {timestamp} UTC)").format(
                time_quantity=uptime_str, timestamp=since
            )
        )

    @commands.group()
    async def embedset(self, ctx: commands.Context):
        """
        Commands for toggling embeds on or off.

        This setting determines whether or not to
        use embeds as a response to a command (for
        commands that support it). The default is to
        use embeds.
        """
        if ctx.invoked_subcommand is None:
            text = _("Embed settings:\n\n")
            global_default = await self.bot._config.embeds()
            text += _("Global default: {}\n").format(global_default)
            if ctx.guild:
                guild_setting = await self.bot._config.guild(ctx.guild).embeds()
                text += _("Guild setting: {}\n").format(guild_setting)
            if ctx.channel:
                channel_setting = await self.bot._config.channel(ctx.channel).embeds()
                text += _("Channel setting: {}\n").format(channel_setting)
            user_setting = await self.bot._config.user(ctx.author).embeds()
            text += _("User setting: {}").format(user_setting)
            await ctx.send(box(text))

    @embedset.command(name="global")
    @checks.is_owner()
    async def embedset_global(self, ctx: commands.Context):
        """
        Toggle the global embed setting.

        This is used as a fallback if the user
        or guild hasn't set a preference. The
        default is to use embeds.
        """
        current = await self.bot._config.embeds()
        await self.bot._config.embeds.set(not current)
        await ctx.send(
            _("Embeds are now {} by default.").format(_("disabled") if current else _("enabled"))
        )

    @embedset.command(name="guild")
    @checks.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    async def embedset_guild(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle the guild's embed setting.

        If enabled is None, the setting will be unset and
        the global default will be used instead.

        If set, this is used instead of the global default
        to determine whether or not to use embeds. This is
        used for all commands done in a guild channel except
        for help commands.
        """
        await self.bot._config.guild(ctx.guild).embeds.set(enabled)
        if enabled is None:
            await ctx.send(_("Embeds will now fall back to the global setting."))
        else:
            await ctx.send(
                _("Embeds are now {} for this guild.").format(
                    _("enabled") if enabled else _("disabled")
                )
            )

    @embedset.command(name="channel")
    @checks.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    async def embedset_channel(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle the channel's embed setting.

        If enabled is None, the setting will be unset and
        the guild default will be used instead.

        If set, this is used instead of the guild default
        to determine whether or not to use embeds. This is
        used for all commands done in a channel except
        for help commands.
        """
        await self.bot._config.channel(ctx.channel).embeds.set(enabled)
        if enabled is None:
            await ctx.send(_("Embeds will now fall back to the global setting."))
        else:
            await ctx.send(
                _("Embeds are now {} for this channel.").format(
                    _("enabled") if enabled else _("disabled")
                )
            )

    @embedset.command(name="user")
    async def embedset_user(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle the user's embed setting.

        If enabled is None, the setting will be unset and
        the global default will be used instead.

        If set, this is used instead of the global default
        to determine whether or not to use embeds. This is
        used for all commands done in a DM with the bot, as
        well as all help commands everywhere.
        """
        await self.bot._config.user(ctx.author).embeds.set(enabled)
        if enabled is None:
            await ctx.send(_("Embeds will now fall back to the global setting."))
        else:
            await ctx.send(
                _("Embeds are now {} for you.").format(_("enabled") if enabled else _("disabled"))
            )

    @commands.command()
    @checks.is_owner()
    async def traceback(self, ctx: commands.Context, public: bool = False):
        """Sends to the owner the last command exception that has occurred

        If public (yes is specified), it will be sent to the chat instead"""
        if not public:
            destination = ctx.author
        else:
            destination = ctx.channel

        if self.bot._last_exception:
            for page in pagify(self.bot._last_exception, shorten_by=10):
                await destination.send(box(page, lang="py"))
        else:
            await ctx.send(_("No exception has occurred yet"))

    @commands.command()
    @commands.check(CoreLogic._can_get_invite_url)
    async def invite(self, ctx):
        """Show's [botname]'s invite url"""
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
        """Setup the bot's invite"""
        pass

    @inviteset.command()
    async def public(self, ctx, confirm: bool = False):
        """
        Define if the command should be accessible for the average user.
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
                "https://discordapp.com/developers/applications/me/{0}".format(self.bot.user.id)
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

        The bot will create its own role with the desired permissions\
        when it joins a new server. This is a special role that can't be\
        deleted or removed from the bot.

        For that, you need to provide a valid permissions level.
        You can generate one here: https://discordapi.com/permissions.html

        Please note that you might need two factor authentification for\
        some permissions.
        """
        await self.bot._config.invite_perm.set(level)
        await ctx.send("The new permissions level has been set.")

    @commands.command()
    @commands.guild_only()
    @checks.is_owner()
    async def leave(self, ctx: commands.Context):
        """Leaves server"""
        await ctx.send(_("Are you sure you want me to leave this server? (y/n)"))

        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred)
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return
        else:
            if pred.result is True:
                await ctx.send(_("Alright. Bye :wave:"))
                log.debug(_("Leaving guild '{}'").format(ctx.guild.name))
                await ctx.guild.leave()
            else:
                await ctx.send(_("Alright, I'll stay then :)"))

    @commands.command()
    @checks.is_owner()
    async def servers(self, ctx: commands.Context):
        """Lists and allows to leave servers"""
        guilds = sorted(list(self.bot.guilds), key=lambda s: s.name.lower())
        msg = ""
        responses = []
        for i, server in enumerate(guilds, 1):
            msg += "{}: {} (`{}`)\n".format(i, server.name, server.id)
            responses.append(str(i))

        for page in pagify(msg, ["\n"]):
            await ctx.send(page)

        query = await ctx.send(_("To leave a server, just type its number."))

        pred = MessagePredicate.contained_in(responses, ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=15)
        except asyncio.TimeoutError:
            try:
                await query.delete()
            except discord.errors.NotFound:
                pass
        else:
            await self.leave_confirmation(guilds[pred.result], ctx)

    async def leave_confirmation(self, guild, ctx):
        if guild.owner.id == ctx.bot.user.id:
            await ctx.send(_("I cannot leave a guild I am the owner of."))
            return

        await ctx.send(_("Are you sure you want me to leave {}? (yes/no)").format(guild.name))
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=15)
            if pred.result is True:
                await guild.leave()
                if guild != ctx.guild:
                    await ctx.send(_("Done."))
            else:
                await ctx.send(_("Alright then."))
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))

    @commands.command()
    @checks.is_owner()
    async def load(self, ctx: commands.Context, *cogs: str):
        """Loads packages"""
        if not cogs:
            return await ctx.send_help()
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            (
                loaded,
                failed,
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
                    " which are marked for removal in Red 3.4: {repo}.\n"
                    "You should inform maintainer of the repo about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in Red 3.4: {repos}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repos=humanize_list([inline(repo) for repo in repos_with_shared_libs]))
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(total_message):
                await ctx.send(page)

    @commands.command()
    @checks.is_owner()
    async def unload(self, ctx: commands.Context, *cogs: str):
        """Unloads packages"""
        if not cogs:
            return await ctx.send_help()
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

    @commands.command(name="reload")
    @checks.is_owner()
    async def reload(self, ctx: commands.Context, *cogs: str):
        """Reloads packages"""
        if not cogs:
            return await ctx.send_help()
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            (
                loaded,
                failed,
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
                    " which are marked for removal in Red 3.4: {repo}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in Red 3.4: {repos}.\n"
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
        """Shuts down the bot"""
        wave = "\N{WAVING HAND SIGN}"
        skin = "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Shutting down... ") + wave + skin)
        await ctx.bot.shutdown()

    @commands.command(name="restart")
    @checks.is_owner()
    async def _restart(self, ctx: commands.Context, silently: bool = False):
        """Attempts to restart Red

        Makes Red quit with exit code 26
        The restart is not guaranteed: it must be dealt
        with by the process manager in use"""
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Restarting..."))
        await ctx.bot.shutdown(restart=True)

    @commands.group(name="set")
    async def _set(self, ctx: commands.Context):
        """Changes [botname]'s settings"""
        if ctx.invoked_subcommand is None:
            if ctx.guild:
                guild = ctx.guild
                admin_role_ids = await ctx.bot._config.guild(ctx.guild).admin_role()
                admin_role_names = [r.name for r in guild.roles if r.id in admin_role_ids]
                admin_roles_str = (
                    humanize_list(admin_role_names) if admin_role_names else "Not Set."
                )
                mod_role_ids = await ctx.bot._config.guild(ctx.guild).mod_role()
                mod_role_names = [r.name for r in guild.roles if r.id in mod_role_ids]
                mod_roles_str = humanize_list(mod_role_names) if mod_role_names else "Not Set."
                guild_settings = _("Admin roles: {admin}\nMod roles: {mod}\n").format(
                    admin=admin_roles_str, mod=mod_roles_str
                )
            else:
                guild_settings = ""

            prefixes = await ctx.bot._prefix_cache.get_prefixes(ctx.guild)
            locale = await ctx.bot._config.locale()
            regional_format = await ctx.bot._config.regional_format() or _("Same as bot's locale")

            prefix_string = " ".join(prefixes)
            settings = _(
                "{bot_name} Settings:\n\n"
                "Prefixes: {prefixes}\n"
                "{guild_settings}"
                "Locale: {locale}\n"
                "Regional format: {regional_format}"
            ).format(
                bot_name=ctx.bot.user.name,
                prefixes=prefix_string,
                guild_settings=guild_settings,
                locale=locale,
                regional_format=regional_format,
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

        The default is "Red V3"
        """
        if not description:
            await ctx.bot._config.description.clear()
            ctx.bot.description = "Red V3"
            await ctx.send(_("Description reset."))
        elif len(description) > 250:  # While the limit is 256, we bold it adding characters.
            await ctx.send(
                _(
                    "This description is too long to properly display. "
                    "Please try again with below 250 characters"
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
        Adds a mod role for this guild.
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

        Default is for fuzzy command search to be disabled.
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

        Default is for fuzzy command search to be disabled.
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
        """
        if colour is None:
            ctx.bot._color = discord.Color.red()
            await ctx.bot._config.color.set(discord.Color.red().value)
            return await ctx.send(_("The color has been reset."))
        ctx.bot._color = colour
        await ctx.bot._config.color.set(colour.value)
        await ctx.send(_("The color has been set."))

    @_set.command()
    @checks.is_owner()
    async def avatar(self, ctx: commands.Context, url: str):
        """Sets [botname]'s avatar"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.read()

        try:
            await ctx.bot.user.edit(avatar=data)
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Failed. Remember that you can edit my avatar "
                    "up to two times a hour. The URL must be a "
                    "direct link to a JPG / PNG."
                )
            )
        except discord.InvalidArgument:
            await ctx.send(_("JPG / PNG format only."))
        else:
            await ctx.send(_("Done."))

    @_set.command(name="playing", aliases=["game"])
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _game(self, ctx: commands.Context, *, game: str = None):
        """Sets [botname]'s playing status"""

        if game:
            if len(game) > 128:
                await ctx.send("The maximum length of game descriptions is 128 characters.")
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
        """Sets [botname]'s listening status"""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if listening:
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
        """Sets [botname]'s watching status"""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if watching:
            activity = discord.Activity(name=watching, type=discord.ActivityType.watching)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(_("Status set to ``Watching {watching}``.").format(watching=watching))
        else:
            await ctx.send(_("Watching cleared."))

    @_set.command()
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def status(self, ctx: commands.Context, *, status: str):
        """Sets [botname]'s status

        Available statuses:
            online
            idle
            dnd
            invisible
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

    @_set.command(name="streaming", aliases=["stream"])
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def stream(self, ctx: commands.Context, streamer=None, *, stream_title=None):
        """Sets [botname]'s streaming status
        Leaving both streamer and stream_title empty will clear it."""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else None

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
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
        """Sets [botname]'s username"""
        try:
            await self._name(name=username)
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Failed to change name. Remember that you can "
                    "only do it up to 2 times an hour. Use "
                    "nicknames if you need frequent changes. "
                    "`{}set nickname`"
                ).format(ctx.clean_prefix)
            )
        else:
            await ctx.send(_("Done."))

    @_set.command(name="nickname")
    @checks.admin()
    @commands.guild_only()
    async def _nickname(self, ctx: commands.Context, *, nickname: str = None):
        """Sets [botname]'s nickname"""
        try:
            await ctx.guild.me.edit(nick=nickname)
        except discord.Forbidden:
            await ctx.send(_("I lack the permissions to change my own nickname."))
        else:
            await ctx.send(_("Done."))

    @_set.command(aliases=["prefixes"])
    @checks.is_owner()
    async def prefix(self, ctx: commands.Context, *prefixes: str):
        """Sets [botname]'s global prefix(es)"""
        if not prefixes:
            await ctx.send_help()
            return
        await self._prefixes(prefixes)
        await ctx.send(_("Prefix set."))

    @_set.command(aliases=["serverprefixes"])
    @checks.admin()
    @commands.guild_only()
    async def serverprefix(self, ctx: commands.Context, *prefixes: str):
        """Sets [botname]'s server prefix(es)"""
        if not prefixes:
            await ctx.bot._prefix_cache.set_prefixes(guild=ctx.guild, prefixes=[])
            await ctx.send(_("Guild prefixes have been reset."))
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot._prefix_cache.set_prefixes(guild=ctx.guild, prefixes=prefixes)
        await ctx.send(_("Prefix set."))

    @_set.command()
    @checks.is_owner()
    async def locale(self, ctx: commands.Context, language_code: str):
        """
        Changes bot's locale.

        `<language_code>` can be any language code with country code included,
        e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.

        Go to Red's Crowdin page to see locales that are available with translations:
        https://translate.discord.red

        To reset to English, use "en-US".
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
        await ctx.bot._config.locale.set(standardized_locale_name)
        await ctx.send(_("Locale has been set."))

    @_set.command(aliases=["region"])
    @checks.is_owner()
    async def regionalformat(self, ctx: commands.Context, language_code: str = None):
        """
        Changes bot's regional format. This is used for formatting date, time and numbers.

        `<language_code>` can be any language code with country code included,
        e.g. `en-US`, `de-DE`, `fr-FR`, `pl-PL`, etc.

        Leave `<language_code>` empty to base regional formatting on bot's locale.
        """
        if language_code is None:
            i18n.set_regional_format(None)
            await ctx.bot._config.regional_format.set(None)
            await ctx.send(_("Regional formatting will now be based on bot's locale."))
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
        await ctx.bot._config.regional_format.set(standardized_locale_name)
        await ctx.send(
            _("Regional formatting will now be based on `{language_code}` locale.").format(
                language_code=standardized_locale_name
            )
        )

    @_set.command()
    @checks.is_owner()
    async def custominfo(self, ctx: commands.Context, *, text: str = None):
        """Customizes a section of [p]info

        The maximum amount of allowed characters is 1024.
        Supports markdown, links and "mentions".
        Link example:
        `[My link](https://example.com)`
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
            await ctx.bot.send(_("Characters must be fewer than 1024."))

    @_set.command()
    @checks.is_owner()
    async def api(self, ctx: commands.Context, service: str, *, tokens: TokenConverter):
        """Set various external API tokens.

        This setting will be asked for by some 3rd party cogs and some core cogs.

        To add the keys provide the service name and the tokens as a comma separated
        list of key,values as described by the cog requesting this command.

        Note: API tokens are sensitive and should only be used in a private channel
        or in DM with the bot.
        """
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await ctx.message.delete()
        await ctx.bot.set_shared_api_tokens(service, **tokens)
        await ctx.send(_("`{service}` API tokens have been set.").format(service=service))

    @commands.group()
    @checks.is_owner()
    async def helpset(self, ctx: commands.Context):
        """Manage settings for the help command."""
        pass

    @helpset.command(name="usemenus")
    async def helpset_usemenus(self, ctx: commands.Context, use_menus: bool = None):
        """
        Allows the help command to be sent as a paginated menu instead of seperate
        messages.

        This defaults to False.
        Using this without a setting will toggle.
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
        This allows the help command to show hidden commands

        This defaults to False.
        Using this without a setting will toggle.
        """
        if show_hidden is None:
            show_hidden = not await ctx.bot._config.help.show_hidden()
        await ctx.bot._config.help.show_hidden.set(show_hidden)
        if show_hidden:
            await ctx.send(_("Help will not filter hidden commands"))
        else:
            await ctx.send(_("Help will filter hidden commands."))

    @helpset.command(name="verifychecks")
    async def helpset_permfilter(self, ctx: commands.Context, verify: bool = None):
        """
        Sets if commands which can't be run in the current context should be
        filtered from help

        Defaults to True.
        Using this without a setting will toggle.
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
        This allows the bot to respond indicating the existence of a specific
        help topic even if the user can't use it.

        Note: This setting on it's own does not fully prevent command enumeration.

        Defaults to False.
        Using this without a setting will toggle.
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

        This setting only applies to embedded help.

        The default value is 1000 characters. The minimum value is 500.
        The maximum is based on the lower of what you provide and what discord allows.

        Please note that setting a relatively small character limit may
        mean some pages will exceed this limit.
        """
        if limit < 500:
            await ctx.send(_("You must give a value of at least 500 characters."))
            return

        await ctx.bot._config.help.page_char_limit.set(limit)
        await ctx.send(_("Done. The character limit per page has been set to {}.").format(limit))

    @helpset.command(name="maxpages")
    async def helpset_maxpages(self, ctx: commands.Context, pages: int):
        """Set the maximum number of help pages sent in a server channel.

        This setting only applies to embedded help.

        If a help message contains more pages than this value, the help message will
        be sent to the command author via DM. This is to help reduce spam in server
        text channels.

        The default value is 2 pages.
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

        This setting only applies to embedded help. If no tagline is
        specified, the default will be used instead.
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

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def contact(self, ctx: commands.Context, *, message: str):
        """Sends a message to the owner"""
        guild = ctx.message.guild
        author = ctx.message.author
        footer = _("User ID: {}").format(author.id)

        if ctx.guild is None:
            source = _("through DM")
        else:
            source = _("from {}").format(guild)
            footer += _(" | Server ID: {}").format(guild.id)

        prefixes = await ctx.bot.get_valid_prefixes()
        prefix = re.sub(rf"<@!?{ctx.me.id}>", f"@{ctx.me.name}", prefixes[0])

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
        """Sends a DM to a user

        This command needs a user id to work.
        To get a user id enable 'developer mode' in Discord's
        settings, 'appearance' tab. Then right click a user
        and copy their id"""
        destination = discord.utils.get(ctx.bot.get_all_members(), id=user_id)
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
        prefix = re.sub(rf"<@!?{ctx.me.id}>", f"@{ctx.me.name}", prefixes[0])
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
        """Shows debug information useful for debugging.."""

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

        if await ctx.embed_requested():
            e = discord.Embed(color=await ctx.embed_colour())
            e.title = "Debug Info for Red"
            e.add_field(name="Red version", value=redver, inline=True)
            e.add_field(name="Python version", value=pyver, inline=True)
            e.add_field(name="Discord.py version", value=dpy_version, inline=True)
            e.add_field(name="Pip version", value=pipver, inline=True)
            e.add_field(name="System arch", value=platform.machine(), inline=True)
            e.add_field(name="User", value=user_who_ran, inline=True)
            e.add_field(name="OS version", value=osver, inline=False)
            e.add_field(
                name="Python executable",
                value=escape(sys.executable, formatting=True),
                inline=False,
            )
            await ctx.send(embed=e)
        else:
            info = (
                "Debug Info for Red\n\n"
                + "Red version: {}\n".format(redver)
                + "Python version: {}\n".format(pyver)
                + "Python executable: {}\n".format(sys.executable)
                + "Discord.py version: {}\n".format(dpy_version)
                + "Pip version: {}\n".format(pipver)
                + "System arch: {}\n".format(platform.machine())
                + "User: {}\n".format(user_who_ran)
                + "OS version: {}\n".format(osver)
            )
            await ctx.send(box(info))

    @commands.group()
    @checks.is_owner()
    async def whitelist(self, ctx: commands.Context):
        """
        Whitelist management commands.
        """
        pass

    @whitelist.command(name="add", usage="<user>...")
    async def whitelist_add(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Adds a user to the whitelist.
        """
        if not users:
            await ctx.send_help()
            return

        uids = [getattr(user, "id", user) for user in users]
        await self.bot._whiteblacklist_cache.add_to_whitelist(None, uids)

        await ctx.send(_("Users added to whitelist."))

    @whitelist.command(name="list")
    async def whitelist_list(self, ctx: commands.Context):
        """
        Lists whitelisted users.
        """
        curr_list = await ctx.bot._config.whitelist()

        if not curr_list:
            await ctx.send("Whitelist is empty.")
            return

        msg = _("Whitelisted Users:")
        for user in curr_list:
            msg += "\n\t- {}".format(user)

        for page in pagify(msg):
            await ctx.send(box(page))

    @whitelist.command(name="remove", usage="<user>...")
    async def whitelist_remove(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Removes user from whitelist.
        """
        if not users:
            await ctx.send_help()
            return

        uids = [getattr(user, "id", user) for user in users]
        await self.bot._whiteblacklist_cache.remove_from_whitelist(None, uids)

        await ctx.send(_("Users have been removed from whitelist."))

    @whitelist.command(name="clear")
    async def whitelist_clear(self, ctx: commands.Context):
        """
        Clears the whitelist.
        """
        await self.bot._whiteblacklist_cache.clear_whitelist()
        await ctx.send(_("Whitelist has been cleared."))

    @commands.group()
    @checks.is_owner()
    async def blacklist(self, ctx: commands.Context):
        """
        Blacklist management commands.
        """
        pass

    @blacklist.command(name="add", usage="<user>...")
    async def blacklist_add(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Adds a user to the blacklist.
        """
        if not users:
            await ctx.send_help()
            return

        for user in users:
            if isinstance(user, int):
                user_obj = discord.Object(id=user)
            else:
                user_obj = user
            if await ctx.bot.is_owner(user_obj):
                await ctx.send(_("You cannot blacklist an owner!"))
                return

        uids = [getattr(user, "id", user) for user in users]
        await self.bot._whiteblacklist_cache.add_to_blacklist(None, uids)

        await ctx.send(_("User added to blacklist."))

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx: commands.Context):
        """
        Lists blacklisted users.
        """
        curr_list = await self.bot._whiteblacklist_cache.get_blacklist(None)

        if not curr_list:
            await ctx.send("Blacklist is empty.")
            return

        msg = _("Blacklisted Users:")
        for user in curr_list:
            msg += "\n\t- {}".format(user)

        for page in pagify(msg):
            await ctx.send(box(page))

    @blacklist.command(name="remove", usage="<user>...")
    async def blacklist_remove(self, ctx: commands.Context, *users: Union[discord.Member, int]):
        """
        Removes user from blacklist.
        """
        if not users:
            await ctx.send_help()
            return

        uids = [getattr(user, "id", user) for user in users]
        await self.bot._whiteblacklist_cache.remove_from_blacklist(None, uids)

        await ctx.send(_("Users have been removed from blacklist."))

    @blacklist.command(name="clear")
    async def blacklist_clear(self, ctx: commands.Context):
        """
        Clears the blacklist.
        """
        await self.bot._whiteblacklist_cache.clear_blacklist()
        await ctx.send(_("Blacklist has been cleared."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def localwhitelist(self, ctx: commands.Context):
        """
        Whitelist management commands.
        """
        pass

    @localwhitelist.command(name="add", usage="<user_or_role>...")
    async def localwhitelist_add(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Adds a user or role to the whitelist.
        """
        if not users_or_roles:
            await ctx.send_help()
            return

        names = [getattr(users_or_roles, "name", users_or_roles) for u_or_r in users_or_roles]
        uids = [getattr(users_or_roles, "id", users_or_roles) for u_or_r in users_or_roles]
        await self.bot._whiteblacklist_cache.add_to_whitelist(ctx.guild, uids)

        await ctx.send(_("{names} added to whitelist.").format(names=humanize_list(names)))

    @localwhitelist.command(name="list")
    async def localwhitelist_list(self, ctx: commands.Context):
        """
        Lists whitelisted users and roles.
        """
        curr_list = await self.bot._whiteblacklist_cache.get_whitelist(ctx.guild)

        if not curr_list:
            await ctx.send("Local whitelist is empty.")
            return

        msg = _("Whitelisted Users and roles:")
        for obj in curr_list:
            msg += "\n\t- {}".format(obj)

        for page in pagify(msg):
            await ctx.send(box(page))

    @localwhitelist.command(name="remove", usage="<user_or_role>...")
    async def localwhitelist_remove(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Removes user or role from whitelist.
        """
        if not users_or_roles:
            await ctx.send_help()
            return

        names = [getattr(users_or_roles, "name", users_or_roles) for u_or_r in users_or_roles]
        uids = [getattr(users_or_roles, "id", users_or_roles) for u_or_r in users_or_roles]
        await self.bot._whiteblacklist_cache.remove_from_whitelist(ctx.guild, uids)

        await ctx.send(
            _("{names} removed from the local whitelist.").format(names=humanize_list(names))
        )

    @localwhitelist.command(name="clear")
    async def localwhitelist_clear(self, ctx: commands.Context):
        """
        Clears the whitelist.
        """
        await self.bot._whiteblacklist_cache.clear_whitelist(ctx.guild)
        await ctx.send(_("Local whitelist has been cleared."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def localblacklist(self, ctx: commands.Context):
        """
        blacklist management commands.
        """
        pass

    @localblacklist.command(name="add", usage="<user_or_role>...")
    async def localblacklist_add(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Adds a user or role to the blacklist.
        """
        if not users_or_roles:
            await ctx.send_help()
            return

        for user_or_role in users_or_roles:
            uid = discord.Object(id=getattr(user_or_role, "id", user_or_role))
            if uid.id == ctx.author.id:
                await ctx.send(_("You cannot blacklist yourself!"))
                return
            if uid.id == ctx.guild.owner_id and not await ctx.bot.is_owner(ctx.author):
                await ctx.send(_("You cannot blacklist the guild owner!"))
                return
            if await ctx.bot.is_owner(uid):
                await ctx.send(_("You cannot blacklist a bot owner!"))
                return
        names = [getattr(users_or_roles, "name", users_or_roles) for u_or_r in users_or_roles]
        uids = [getattr(users_or_roles, "id", users_or_roles) for u_or_r in users_or_roles]
        await self.bot._whiteblacklist_cache.add_to_blacklist(ctx.guild, uids)

        await ctx.send(
            _("{names} added to the local blacklist.").format(names=humanize_list(names))
        )

    @localblacklist.command(name="list")
    async def localblacklist_list(self, ctx: commands.Context):
        """
        Lists blacklisted users and roles.
        """
        curr_list = await self.bot._whiteblacklist_cache.get_blacklist(ctx.guild)

        if not curr_list:
            await ctx.send("Local blacklist is empty.")
            return

        msg = _("Blacklisted Users and Roles:")
        for obj in curr_list:
            msg += "\n\t- {}".format(obj)

        for page in pagify(msg):
            await ctx.send(box(page))

    @localblacklist.command(name="remove", usage="<user_or_role>...")
    async def localblacklist_remove(
        self, ctx: commands.Context, *users_or_roles: Union[discord.Member, discord.Role, int]
    ):
        """
        Removes user or role from blacklist.
        """
        if not users_or_roles:
            await ctx.send_help()
            return

        names = [getattr(users_or_roles, "name", users_or_roles) for u_or_r in users_or_roles]
        uids = [getattr(users_or_roles, "id", users_or_roles) for u_or_r in users_or_roles]
        await self.bot._whiteblacklist_cache.remove_from_whitelist(ctx.guild, uids)

        await ctx.send(
            _("{names} removed from the local blacklist.").format(names=humanize_list(names))
        )

    @localblacklist.command(name="clear")
    async def localblacklist_clear(self, ctx: commands.Context):
        """
        Clears the blacklist.
        """
        await ctx.bot._config.guild(ctx.guild).blacklist.set([])
        await ctx.send(_("Local blacklist has been cleared."))

    @checks.guildowner_or_permissions(administrator=True)
    @commands.group(name="command")
    async def command_manager(self, ctx: commands.Context):
        """Manage the bot's commands."""
        pass

    @command_manager.group(name="listdisabled", invoke_without_command=True)
    async def list_disabled(self, ctx: commands.Context):
        """
        List disabled commands.

        If you're the bot owner, this will show global disabled commands by default.
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.list_disabled_global)
        else:
            await ctx.invoke(self.list_disabled_guild)

    @list_disabled.command(name="global")
    async def list_disabled_global(self, ctx: commands.Context):
        """List disabled commands globally."""
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

    @list_disabled.command(name="guild")
    async def list_disabled_guild(self, ctx: commands.Context):
        """List disabled commands in this server."""
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
        """Disable a command.

        If you're the bot owner, this will disable commands
        globally by default.
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_disable_global, command=command)
        else:
            await ctx.invoke(self.command_disable_guild, command=command)

    @checks.is_owner()
    @command_disable.command(name="global")
    async def command_disable_global(self, ctx: commands.Context, *, command: str):
        """Disable a command globally."""
        command_obj: commands.Command = ctx.bot.get_command(command)
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

        if isinstance(command_obj, commands.commands._AlwaysAvailableCommand):
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
        """Disable a command in this server only."""
        command_obj: commands.Command = ctx.bot.get_command(command)
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

        if isinstance(command_obj, commands.commands._AlwaysAvailableCommand):
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

        If you're a bot owner, this will try to enable a globally
        disabled command by default.
        """
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_enable_global, command=command)
        else:
            await ctx.invoke(self.command_enable_guild, command=command)

    @commands.is_owner()
    @command_enable.command(name="global")
    async def command_enable_global(self, ctx: commands.Context, *, command: str):
        """Enable a command globally."""
        command_obj: commands.Command = ctx.bot.get_command(command)
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
        """Enable a command in this server."""
        command_obj: commands.Command = ctx.bot.get_command(command)
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

        To include the command name in the message, include the
        `{command}` placeholder.
        """
        await ctx.bot._config.disabled_command_msg.set(message)
        await ctx.tick()

    @commands.guild_only()
    @checks.guildowner_or_permissions(manage_guild=True)
    @commands.group(name="autoimmune")
    async def autoimmune_group(self, ctx: commands.Context):
        """
        Server settings for immunity from automated actions
        """
        pass

    @autoimmune_group.command(name="list")
    async def autoimmune_list(self, ctx: commands.Context):
        """
        Get's the current members and roles

        configured for automatic moderation action immunity
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
            output = _("No immunty settings here.")

        for page in pagify(output):
            await ctx.send(page)

    @autoimmune_group.command(name="add")
    async def autoimmune_add(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Makes a user or roles immune from automated moderation actions
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
        Makes a user or roles immune from automated moderation actions
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
        Checks if a user or role would be considered immune from automated actions
        """

        if await ctx.bot.is_automod_immune(user_or_role):
            await ctx.send(_("They are immune"))
        else:
            await ctx.send(_("They are not Immune"))

    @checks.is_owner()
    @_set.group()
    async def ownernotifications(self, ctx: commands.Context):
        """
        Commands for configuring owner notifications.
        """
        pass

    @ownernotifications.command()
    async def optin(self, ctx: commands.Context):
        """
        Opt-in on recieving owner notifications.

        This is the default state.
        """
        async with ctx.bot._config.owner_opt_out_list() as opt_outs:
            if ctx.author.id in opt_outs:
                opt_outs.remove(ctx.author.id)

        await ctx.tick()

    @ownernotifications.command()
    async def optout(self, ctx: commands.Context):
        """
        Opt-out of recieving owner notifications.
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
        Adds a destination text channel to recieve owner notifications
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
        Removes a destination text channel from recieving owner notifications.
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
        Lists the configured extra destinations for owner notifications
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
        """Add servers or channels to the ignore list."""
        if ctx.invoked_subcommand is None:
            for page in pagify(await self.count_ignored(ctx)):
                await ctx.maybe_send_embed(page)

    @ignore.command(name="channel")
    async def ignore_channel(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Ignore commands in the channel or category.

        Defaults to the current channel.
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
        """Ignore commands in this server."""
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
        """Remove servers or channels from the ignore list."""
        if ctx.invoked_subcommand is None:
            for page in pagify(await self.count_ignored(ctx)):
                await ctx.maybe_send_embed(page)

    @unignore.command(name="channel")
    async def unignore_channel(
        self,
        ctx: commands.Context,
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]] = None,
    ):
        """Remove a channel or category from ignore the list.

        Defaults to the current channel.
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
        """Remove this server from the ignore list."""
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
                continue
            else:
                continue
            if await self.bot._ignored_cache.get_ignored_channel(channel):
                text_channels.append(channel)

        cat_str = (
            humanize_list([c.name for c in category_channels]) if category_channels else "None"
        )
        chan_str = humanize_list([c.mention for c in text_channels]) if text_channels else "None"
        msg = _("Currently ignored categories: {categories}\nChannels:{channels}").format(
            categories=cat_str, channels=chan_str
        )
        return msg


# Removing this command from forks is a violation of the GPLv3 under which it is licensed.
# Otherwise interfering with the ability for this command to be accessible is also a violation.
@commands.command(
    cls=commands.commands._AlwaysAvailableCommand,
    name="licenseinfo",
    aliases=["licenceinfo"],
    i18n=_,
)
async def license_info_command(ctx):
    """
    Get info about Red's licenses
    """

    message = (
        "This bot is an instance of Red-DiscordBot (hereafter referred to as Red)\n"
        "Red is a free and open source application made available to the public and "
        "licensed under the GNU GPLv3. The full text of this license is available to you at "
        "<https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/LICENSE>"
    )
    await ctx.send(message)
    # We need a link which contains a thank you to other projects which we use at some point.
