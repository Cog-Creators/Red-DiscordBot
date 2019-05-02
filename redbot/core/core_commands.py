import asyncio
import contextlib
import datetime
import importlib
import itertools
import json
import logging
import os
import pathlib
import sys
import tarfile
import traceback
from collections import namedtuple
from pathlib import Path
from random import SystemRandom
from string import ascii_letters, digits
from typing import TYPE_CHECKING, Union, Tuple, List, Optional, Iterable, Sequence, Dict

import aiohttp
import discord
import pkg_resources

from redbot.core import (
    __version__,
    version_info as red_version_info,
    VersionInfo,
    checks,
    commands,
    errors,
    i18n,
)
from .utils.predicates import MessagePredicate
from .utils.chat_formatting import pagify, box, inline

if TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["Core"]

log = logging.getLogger("red")


_ = i18n.Translator("Core", __file__)


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
    ) -> Tuple[List[str], List[str], List[str], List[str], List[Tuple[str, str]]]:
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

        bot = self.bot

        cogspecs = []

        for name in cog_names:
            try:
                spec = await bot.cog_mgr.find_cog(name)
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

        return (
            loaded_packages,
            failed_packages,
            notfound_packages,
            alreadyloaded_packages,
            failed_with_reason_packages,
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

    @staticmethod
    def _get_package_strings(
        packages: List[str], fmt: str, other: Optional[Tuple[str, ...]] = None
    ) -> str:
        """
        Gets the strings needed for the load, unload and reload commands
        """
        packages = [inline(name) for name in packages]

        if other is None:
            other = ("", "")
        plural = "s" if len(packages) > 1 else ""
        use_and, other = ("", other[0]) if len(packages) == 1 else (" and ", other[1])
        packages_string = ", ".join(packages[:-1]) + use_and + packages[-1]

        form = {"plural": plural, "packs": packages_string, "other": other}
        final_string = fmt.format(**form)
        return final_string

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
    ) -> Tuple[List[str], List[str], List[str], List[str], List[Tuple[str, str]]]:
        await self._unload(cog_names)

        loaded, load_failed, not_found, already_loaded, load_failed_with_reason = await self._load(
            cog_names
        )

        return loaded, load_failed, not_found, already_loaded, load_failed_with_reason

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
            prefixes = sorted(prefixes, reverse=True)
            await self.bot.db.prefix.set(prefixes)
        return await self.bot.db.prefix()

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
        return discord.utils.oauth_url(app_info.id)


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
        red_pypi = "https://pypi.python.org/pypi/Red-DiscordBot"
        support_server_url = "https://discord.gg/red"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days
        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        python_version = "[{}.{}.{}]({})".format(*sys.version_info[:3], python_url)
        red_version = "[{}]({})".format(__version__, red_pypi)
        app_info = await self.bot.application_info()
        owner = app_info.owner
        custom_info = await self.bot.db.custom_info()

        async with aiohttp.ClientSession() as session:
            async with session.get("{}/json".format(red_pypi)) as r:
                data = await r.json()
        outdated = VersionInfo.from_str(data["info"]["version"]) > red_version_info
        about = _(
            "This is an instance of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and [improved by many]({}).\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
        ).format(red_repo, author_repo, org_repo, support_server_url)

        embed = discord.Embed(color=(await ctx.embed_colour()))
        embed.add_field(name=_("Instance owned by"), value=str(owner))
        embed.add_field(name="Python", value=python_version)
        embed.add_field(name="discord.py", value=dpy_version)
        embed.add_field(name=_("Red version"), value=red_version)
        if outdated:
            embed.add_field(
                name=_("Outdated"), value=_("Yes, {} is available").format(data["info"]["version"])
            )
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
        """Shows Red's uptime"""
        since = ctx.bot.uptime.strftime("%Y-%m-%d %H:%M:%S")
        passed = self.get_bot_uptime()
        await ctx.send(_("Been up for: **{}** (since {} UTC)").format(passed, since))

    def get_bot_uptime(self, *, brief: bool = False):
        # Courtesy of Danny
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = _("{d} days, {h} hours, {m} minutes, and {s} seconds")
            else:
                fmt = _("{h} hours, {m} minutes, and {s} seconds")
        else:
            fmt = _("{h}h {m}m {s}s")
            if days:
                fmt = _("{d}d ") + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

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
            global_default = await self.bot.db.embeds()
            text += _("Global default: {}\n").format(global_default)
            if ctx.guild:
                guild_setting = await self.bot.db.guild(ctx.guild).embeds()
                text += _("Guild setting: {}\n").format(guild_setting)
            user_setting = await self.bot.db.user(ctx.author).embeds()
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
        current = await self.bot.db.embeds()
        await self.bot.db.embeds.set(not current)
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
        await self.bot.db.guild(ctx.guild).embeds.set(enabled)
        if enabled is None:
            await ctx.send(_("Embeds will now fall back to the global setting."))
        else:
            await ctx.send(
                _("Embeds are now {} for this guild.").format(
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
        await self.bot.db.user(ctx.author).embeds.set(enabled)
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
    @checks.is_owner()
    async def invite(self, ctx: commands.Context):
        """Show's Red's invite url"""
        await ctx.author.send(await self._invite_url())

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
            msg += "{}: {}\n".format(i, server.name)
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
        async with ctx.typing():
            loaded, failed, not_found, already_loaded, failed_with_reason = await self._load(cogs)

        if loaded:
            fmt = _("Loaded {packs}.")
            formed = self._get_package_strings(loaded, fmt)
            await ctx.send(formed)

        if already_loaded:
            fmt = _("The package{plural} {packs} {other} already loaded.")
            formed = self._get_package_strings(already_loaded, fmt, (_("is"), _("are")))
            await ctx.send(formed)

        if failed:
            fmt = _(
                "Failed to load package{plural} {packs}. Check your console or "
                "logs for details."
            )
            formed = self._get_package_strings(failed, fmt)
            await ctx.send(formed)

        if not_found:
            fmt = _("The package{plural} {packs} {other} not found in any cog path.")
            formed = self._get_package_strings(not_found, fmt, (_("was"), _("were")))
            await ctx.send(formed)

        if failed_with_reason:
            fmt = _(
                "{other} package{plural} could not be loaded for the following reason{plural}:\n\n"
            )
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason])
            formed = self._get_package_strings(
                [x for x, y in failed_with_reason], fmt, (_("This"), _("These"))
            )
            await ctx.send(formed + reasons)

    @commands.command()
    @checks.is_owner()
    async def unload(self, ctx: commands.Context, *cogs: str):
        """Unloads packages"""
        if not cogs:
            return await ctx.send_help()
        unloaded, failed = await self._unload(cogs)

        if unloaded:
            fmt = _("Package{plural} {packs} {other} unloaded.")
            formed = self._get_package_strings(unloaded, fmt, (_("was"), _("were")))
            await ctx.send(formed)

        if failed:
            fmt = _("The package{plural} {packs} {other} not loaded.")
            formed = self._get_package_strings(failed, fmt, (_("is"), _("are")))
            await ctx.send(formed)

    @commands.command(name="reload")
    @checks.is_owner()
    async def reload(self, ctx: commands.Context, *cogs: str):
        """Reloads packages"""
        if not cogs:
            return await ctx.send_help()
        async with ctx.typing():
            loaded, failed, not_found, already_loaded, failed_with_reason = await self._reload(
                cogs
            )

        if loaded:
            fmt = _("Package{plural} {packs} {other} reloaded.")
            formed = self._get_package_strings(loaded, fmt, (_("was"), _("were")))
            await ctx.send(formed)

        if failed:
            fmt = _("Failed to reload package{plural} {packs}. Check your logs for details")
            formed = self._get_package_strings(failed, fmt)
            await ctx.send(formed)

        if not_found:
            fmt = _("The package{plural} {packs} {other} not found in any cog path.")
            formed = self._get_package_strings(not_found, fmt, (_("was"), _("were")))
            await ctx.send(formed)

        if failed_with_reason:
            fmt = _(
                "{other} package{plural} could not be reloaded for the following reason{plural}:\n\n"
            )
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason])
            formed = self._get_package_strings(
                [x for x, y in failed_with_reason], fmt, (_("This"), _("These"))
            )
            await ctx.send(formed + reasons)

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
        """Changes Red's settings"""
        if ctx.invoked_subcommand is None:
            if ctx.guild:
                guild = ctx.guild
                admin_role = (
                    guild.get_role(await ctx.bot.db.guild(ctx.guild).admin_role()) or "Not set"
                )
                mod_role = (
                    guild.get_role(await ctx.bot.db.guild(ctx.guild).mod_role()) or "Not set"
                )
                prefixes = await ctx.bot.db.guild(ctx.guild).prefix()
                guild_settings = _("Admin role: {admin}\nMod role: {mod}\n").format(
                    admin=admin_role, mod=mod_role
                )
            else:
                guild_settings = ""
                prefixes = None  # This is correct. The below can happen in a guild.
            if not prefixes:
                prefixes = await ctx.bot.db.prefix()
            locale = await ctx.bot.db.locale()

            prefix_string = " ".join(prefixes)
            settings = _(
                "{bot_name} Settings:\n\n"
                "Prefixes: {prefixes}\n"
                "{guild_settings}"
                "Locale: {locale}"
            ).format(
                bot_name=ctx.bot.user.name,
                prefixes=prefix_string,
                guild_settings=guild_settings,
                locale=locale,
            )
            await ctx.send(box(settings))

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def adminrole(self, ctx: commands.Context, *, role: discord.Role):
        """Sets the admin role for this server"""
        await ctx.bot.db.guild(ctx.guild).admin_role.set(role.id)
        await ctx.send(_("The admin role for this guild has been set."))

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def modrole(self, ctx: commands.Context, *, role: discord.Role):
        """Sets the mod role for this server"""
        await ctx.bot.db.guild(ctx.guild).mod_role.set(role.id)
        await ctx.send(_("The mod role for this guild has been set."))

    @_set.command(aliases=["usebotcolor"])
    @checks.guildowner()
    @commands.guild_only()
    async def usebotcolour(self, ctx: commands.Context):
        """
        Toggle whether to use the bot owner-configured colour for embeds.

        Default is to not use the bot's configured colour, in which case the
        colour used will be the colour of the bot's top role.
        """
        current_setting = await ctx.bot.db.guild(ctx.guild).use_bot_color()
        await ctx.bot.db.guild(ctx.guild).use_bot_color.set(not current_setting)
        await ctx.send(
            _("The bot {} use its configured color for embeds.").format(
                _("will not") if current_setting else _("will")
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
        current_setting = await ctx.bot.db.guild(ctx.guild).fuzzy()
        await ctx.bot.db.guild(ctx.guild).fuzzy.set(not current_setting)
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
        current_setting = await ctx.bot.db.fuzzy()
        await ctx.bot.db.fuzzy.set(not current_setting)
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

        http://discordpy.readthedocs.io/en/rewrite/ext/commands/api.html#discord.ext.commands.ColourConverter
        """
        if colour is None:
            ctx.bot.color = discord.Color.red()
            await ctx.bot.db.color.set(discord.Color.red().value)
            return await ctx.send(_("The color has been reset."))
        ctx.bot.color = colour
        await ctx.bot.db.color.set(colour.value)
        await ctx.send(_("The color has been set."))

    @_set.command()
    @checks.is_owner()
    async def avatar(self, ctx: commands.Context, url: str):
        """Sets Red's avatar"""
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

    @_set.command(name="game")
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _game(self, ctx: commands.Context, *, game: str = None):
        """Sets Red's playing status"""

        if game:
            game = discord.Game(name=game)
        else:
            game = None
        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        await ctx.bot.change_presence(status=status, activity=game)
        await ctx.send(_("Game set."))

    @_set.command(name="listening")
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _listening(self, ctx: commands.Context, *, listening: str = None):
        """Sets Red's listening status"""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if listening:
            activity = discord.Activity(name=listening, type=discord.ActivityType.listening)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        await ctx.send(_("Listening set."))

    @_set.command(name="watching")
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def _watching(self, ctx: commands.Context, *, watching: str = None):
        """Sets Red's watching status"""

        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else discord.Status.online
        if watching:
            activity = discord.Activity(name=watching, type=discord.ActivityType.watching)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        await ctx.send(_("Watching set."))

    @_set.command()
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def status(self, ctx: commands.Context, *, status: str):
        """Sets Red's status

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

    @_set.command()
    @checks.bot_in_a_guild()
    @checks.is_owner()
    async def stream(self, ctx: commands.Context, streamer=None, *, stream_title=None):
        """Sets Red's streaming status
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
        """Sets Red's username"""
        try:
            await self._name(name=username)
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Failed to change name. Remember that you can "
                    "only do it up to 2 times an hour. Use "
                    "nicknames if you need frequent changes. "
                    "`{}set nickname`"
                ).format(ctx.prefix)
            )
        else:
            await ctx.send(_("Done."))

    @_set.command(name="nickname")
    @checks.admin()
    @commands.guild_only()
    async def _nickname(self, ctx: commands.Context, *, nickname: str = None):
        """Sets Red's nickname"""
        try:
            await ctx.guild.me.edit(nick=nickname)
        except discord.Forbidden:
            await ctx.send(_("I lack the permissions to change my own nickname."))
        else:
            await ctx.send(_("Done."))

    @_set.command(aliases=["prefixes"])
    @checks.is_owner()
    async def prefix(self, ctx: commands.Context, *prefixes: str):
        """Sets Red's global prefix(es)"""
        if not prefixes:
            await ctx.send_help()
            return
        await self._prefixes(prefixes)
        await ctx.send(_("Prefix set."))

    @_set.command(aliases=["serverprefixes"])
    @checks.admin()
    @commands.guild_only()
    async def serverprefix(self, ctx: commands.Context, *prefixes: str):
        """Sets Red's server prefix(es)"""
        if not prefixes:
            await ctx.bot.db.guild(ctx.guild).prefix.set([])
            await ctx.send(_("Guild prefixes have been reset."))
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.db.guild(ctx.guild).prefix.set(prefixes)
        await ctx.send(_("Prefix set."))

    @_set.command()
    @commands.cooldown(1, 60 * 10, commands.BucketType.default)
    async def owner(self, ctx: commands.Context):
        """Sets Red's main owner"""
        # According to the Python docs this is suitable for cryptographic use
        random = SystemRandom()
        length = random.randint(25, 35)
        chars = ascii_letters + digits
        token = ""

        for i in range(length):
            token += random.choice(chars)
        log.info(_("{0} ({0.id}) requested to be set as owner.").format(ctx.author))
        print(_("\nVerification token:"))
        print(token)

        owner_disclaimer = _(
            "⚠ **Only** the person who is hosting Red should be "
            "owner. **This has SERIOUS security implications. The "
            "owner can access any data that is present on the host "
            "system.** ⚠"
        )
        await ctx.send(_("Remember:\n") + owner_disclaimer)
        await asyncio.sleep(5)

        await ctx.send(
            _(
                "I have printed a one-time token in the console. "
                "Copy and paste it here to confirm you are the owner."
            )
        )

        try:
            message = await ctx.bot.wait_for(
                "message", check=MessagePredicate.same_context(ctx), timeout=60
            )
        except asyncio.TimeoutError:
            self.owner.reset_cooldown(ctx)
            await ctx.send(
                _("The `{prefix}set owner` request has timed out.").format(prefix=ctx.prefix)
            )
        else:
            if message.content.strip() == token:
                self.owner.reset_cooldown(ctx)
                await ctx.bot.db.owner.set(ctx.author.id)
                ctx.bot.owner_id = ctx.author.id
                await ctx.send(_("You have been set as owner."))
            else:
                await ctx.send(_("Invalid token."))

    @_set.command()
    @checks.is_owner()
    async def token(self, ctx: commands.Context, token: str):
        """Change bot token."""

        if not isinstance(ctx.channel, discord.DMChannel):

            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass

            await ctx.send(
                _(
                    "Please use that command in DM. Since users probably saw your token,"
                    " it is recommended to reset it right now. Go to the following link and"
                    " select `Reveal Token` and `Generate a new token?`."
                    "\n\nhttps://discordapp.com/developers/applications/me/{}"
                ).format(self.bot.user.id)
            )
            return

        await ctx.bot.db.token.set(token)
        await ctx.send(_("Token set. Restart me."))

    @_set.command()
    @checks.is_owner()
    async def locale(self, ctx: commands.Context, locale_name: str):
        """
        Changes bot locale.

        Use [p]listlocales to get a list of available locales.

        To reset to English, use "en-US".
        """
        red_dist = pkg_resources.get_distribution("red-discordbot")
        red_path = Path(red_dist.location) / "redbot"
        locale_list = [loc.stem.lower() for loc in list(red_path.glob("**/*.po"))]
        if locale_name.lower() in locale_list or locale_name.lower() == "en-us":
            i18n.set_locale(locale_name)
            await ctx.bot.db.locale.set(locale_name)
            await ctx.send(_("Locale has been set."))
        else:
            await ctx.send(
                _(
                    "Invalid locale. Use `{prefix}listlocales` to get "
                    "a list of available locales."
                ).format(prefix=ctx.prefix)
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
            await ctx.bot.db.custom_info.clear()
            await ctx.send(_("The custom text has been cleared."))
            return
        if len(text) <= 1024:
            await ctx.bot.db.custom_info.set(text)
            await ctx.send(_("The custom text has been set."))
            await ctx.invoke(self.info)
        else:
            await ctx.bot.send(_("Characters must be fewer than 1024."))

    @_set.command()
    @checks.is_owner()
    async def api(self, ctx: commands.Context, service: str, *tokens: commands.converter.APIToken):
        """Set various external API tokens.
        
        This setting will be asked for by some 3rd party cogs and some core cogs.

        To add the keys provide the service name and the tokens as a comma separated
        list of key,values as described by the cog requesting this command.

        Note: API tokens are sensitive and should only be used in a private channel
        or in DM with the bot.
        """
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            await ctx.message.delete()
        entry = {k: v for t in tokens for k, v in t.items()}
        await ctx.bot.db.api_tokens.set_raw(service, value=entry)
        await ctx.send(_("`{service}` API tokens have been set.").format(service=service))

    @commands.group()
    @checks.is_owner()
    async def helpset(self, ctx: commands.Context):
        """Manage settings for the help command."""
        pass

    @helpset.command(name="pagecharlimit")
    async def helpset_pagecharlimt(self, ctx: commands.Context, limit: int):
        """Set the character limit for each page in the help message.

        This setting only applies to embedded help.

        Please note that setting a relitavely small character limit may
        mean some pages will exceed this limit. This is because categories
        are never spread across multiple pages in the help message.

        The default value is 1000 characters.
        """
        if limit <= 0:
            await ctx.send(_("You must give a positive value!"))
            return

        await ctx.bot.db.help.page_char_limit.set(limit)
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

        await ctx.bot.db.help.max_pages_in_guild.set(pages)
        await ctx.send(_("Done. The page limit has been set to {}.").format(pages))

    @helpset.command(name="tagline")
    async def helpset_tagline(self, ctx: commands.Context, *, tagline: str = None):
        """
        Set the tagline to be used.

        This setting only applies to embedded help. If no tagline is
        specified, the default will be used instead.
        """
        if tagline is None:
            await ctx.bot.db.help.tagline.set("")
            return await ctx.send(_("The tagline has been reset."))

        if len(tagline) > 2048:
            await ctx.send(
                _(
                    "Your tagline is too long! Please shorten it to be "
                    "no more than 2048 characters long."
                )
            )
            return

        await ctx.bot.db.help.tagline.set(tagline)
        await ctx.send(_("The tagline has been set to {}.").format(tagline[:1900]))

    @commands.command()
    @checks.is_owner()
    async def listlocales(self, ctx: commands.Context):
        """
        Lists all available locales

        Use `[p]set locale` to set a locale
        """
        async with ctx.channel.typing():
            red_dist = pkg_resources.get_distribution("red-discordbot")
            red_path = Path(red_dist.location) / "redbot"
            locale_list = [loc.stem for loc in list(red_path.glob("**/*.po"))]
            locale_list.append("en-US")
            locale_list = sorted(set(locale_list))
            if not locale_list:
                await ctx.send(_("No languages found."))
                return
            pages = pagify("\n".join(locale_list), shorten_by=26)

        await ctx.send_interactive(pages, box_lang="Available Locales:")

    @commands.command()
    @checks.is_owner()
    async def backup(self, ctx: commands.Context, *, backup_path: str = None):
        """Creates a backup of all data for the instance."""
        if backup_path:
            path = pathlib.Path(backup_path)
            if not (path.exists() and path.is_dir()):
                return await ctx.send(
                    _("That path doesn't seem to exist.  Please provide a valid path.")
                )
        from redbot.core.data_manager import basic_config, instance_name
        from redbot.core.drivers.red_json import JSON

        data_dir = Path(basic_config["DATA_PATH"])
        if basic_config["STORAGE_TYPE"] == "MongoDB":
            from redbot.core.drivers.red_mongo import Mongo

            m = Mongo("Core", "0", **basic_config["STORAGE_DETAILS"])
            db = m.db
            collection_names = await db.list_collection_names()
            for c_name in collection_names:
                if c_name == "Core":
                    c_data_path = data_dir / basic_config["CORE_PATH_APPEND"]
                else:
                    c_data_path = data_dir / basic_config["COG_PATH_APPEND"] / c_name
                docs = await db[c_name].find().to_list(None)
                for item in docs:
                    item_id = str(item.pop("_id"))
                    output = item
                    target = JSON(c_name, item_id, data_path_override=c_data_path)
                    await target.jsonIO._threadsafe_save_json(output)
        backup_filename = "redv3-{}-{}.tar.gz".format(
            instance_name, ctx.message.created_at.strftime("%Y-%m-%d %H-%M-%S")
        )
        if data_dir.exists():
            if not backup_path:
                backup_pth = data_dir.home()
            else:
                backup_pth = Path(backup_path)
            backup_file = backup_pth / backup_filename

            to_backup = []
            exclusions = [
                "__pycache__",
                "Lavalink.jar",
                os.path.join("Downloader", "lib"),
                os.path.join("CogManager", "cogs"),
                os.path.join("RepoManager", "repos"),
            ]
            downloader_cog = ctx.bot.get_cog("Downloader")
            if downloader_cog and hasattr(downloader_cog, "_repo_manager"):
                repo_output = []
                repo_mgr = downloader_cog._repo_manager
                for repo in repo_mgr._repos.values():
                    repo_output.append({"url": repo.url, "name": repo.name, "branch": repo.branch})
                repo_filename = data_dir / "cogs" / "RepoManager" / "repos.json"
                with open(str(repo_filename), "w") as f:
                    f.write(json.dumps(repo_output, indent=4))
            instance_data = {instance_name: basic_config}
            instance_file = data_dir / "instance.json"
            with open(str(instance_file), "w") as instance_out:
                instance_out.write(json.dumps(instance_data, indent=4))
            for f in data_dir.glob("**/*"):
                if not any(ex in str(f) for ex in exclusions):
                    to_backup.append(f)
            with tarfile.open(str(backup_file), "w:gz") as tar:
                for f in to_backup:
                    tar.add(str(f), recursive=False)
            print(str(backup_file))
            await ctx.send(
                _("A backup has been made of this instance. It is at {}.").format(backup_file)
            )
            if backup_file.stat().st_size > 8_000_000:
                await ctx.send(_("This backup is to large to send via DM."))
                return
            await ctx.send(_("Would you like to receive a copy via DM? (y/n)"))

            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await ctx.bot.wait_for("message", check=pred, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send(_("Response timed out."))
            else:
                if pred.result is True:
                    await ctx.send(_("OK, it's on its way!"))
                    try:
                        async with ctx.author.typing():
                            await ctx.author.send(
                                _("Here's a copy of the backup"),
                                file=discord.File(str(backup_file)),
                            )
                    except discord.Forbidden:
                        await ctx.send(
                            _("I don't seem to be able to DM you. Do you have closed DMs?")
                        )
                    except discord.HTTPException:
                        await ctx.send(_("I could not send the backup file."))
                else:
                    await ctx.send(_("OK then."))
        else:
            await ctx.send(_("That directory doesn't seem to exist..."))

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def contact(self, ctx: commands.Context, *, message: str):
        """Sends a message to the owner"""
        guild = ctx.message.guild
        owner = discord.utils.get(ctx.bot.get_all_members(), id=ctx.bot.owner_id)
        author = ctx.message.author
        footer = _("User ID: {}").format(author.id)

        if ctx.guild is None:
            source = _("through DM")
        else:
            source = _("from {}").format(guild)
            footer += _(" | Server ID: {}").format(guild.id)

        # We need to grab the DM command prefix (global)
        # Since it can also be set through cli flags, bot.db is not a reliable
        # source. So we'll just mock a DM message instead.
        fake_message = namedtuple("Message", "guild")
        prefixes = await ctx.bot.command_prefix(ctx.bot, fake_message(guild=None))
        prefix = prefixes[0]

        content = _("Use `{}dm {} <text>` to reply to this user").format(prefix, author.id)

        description = _("Sent by {} {}").format(author, source)

        if isinstance(author, discord.Member):
            colour = author.colour
        else:
            colour = discord.Colour.red()

        if await ctx.embed_requested():
            e = discord.Embed(colour=colour, description=message)
            if author.avatar_url:
                e.set_author(name=description, icon_url=author.avatar_url)
            else:
                e.set_author(name=description)
            e.set_footer(text=footer)

            try:
                await owner.send(content, embed=e)
            except discord.InvalidArgument:
                await ctx.send(
                    _("I cannot send your message, I'm unable to find my owner... *sigh*")
                )
            except discord.HTTPException:
                await ctx.send(_("I'm unable to deliver your message. Sorry."))
            else:
                await ctx.send(_("Your message has been sent."))
        else:
            msg_text = "{}\nMessage:\n\n{}\n{}".format(description, message, footer)
            try:
                await owner.send("{}\n{}".format(content, box(msg_text)))
            except discord.InvalidArgument:
                await ctx.send(
                    _("I cannot send your message, I'm unable to find my owner... *sigh*")
                )
            except discord.HTTPException:
                await ctx.send(_("I'm unable to deliver your message. Sorry."))
            else:
                await ctx.send(_("Your message has been sent."))

    @commands.command()
    @checks.is_owner()
    async def dm(self, ctx: commands.Context, user_id: int, *, message: str):
        """Sends a DM to a user

        This command needs a user id to work.
        To get a user id enable 'developer mode' in Discord's
        settings, 'appearance' tab. Then right click a user
        and copy their id"""
        destination = discord.utils.get(ctx.bot.get_all_members(), id=user_id)
        if destination is None:
            await ctx.send(
                _(
                    "Invalid ID or user not found. You can only "
                    "send messages to people I share a server "
                    "with."
                )
            )
            return

        fake_message = namedtuple("Message", "guild")
        prefixes = await ctx.bot.command_prefix(ctx.bot, fake_message(guild=None))
        prefix = prefixes[0]
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

    @commands.group()
    @checks.is_owner()
    async def whitelist(self, ctx: commands.Context):
        """
        Whitelist management commands.
        """
        pass

    @whitelist.command(name="add")
    async def whitelist_add(self, ctx, user: discord.User):
        """
        Adds a user to the whitelist.
        """
        async with ctx.bot.db.whitelist() as curr_list:
            if user.id not in curr_list:
                curr_list.append(user.id)

        await ctx.send(_("User added to whitelist."))

    @whitelist.command(name="list")
    async def whitelist_list(self, ctx: commands.Context):
        """
        Lists whitelisted users.
        """
        curr_list = await ctx.bot.db.whitelist()

        msg = _("Whitelisted Users:")
        for user in curr_list:
            msg += "\n\t- {}".format(user)

        for page in pagify(msg):
            await ctx.send(box(page))

    @whitelist.command(name="remove")
    async def whitelist_remove(self, ctx: commands.Context, *, user: discord.User):
        """
        Removes user from whitelist.
        """
        removed = False

        async with ctx.bot.db.whitelist() as curr_list:
            if user.id in curr_list:
                removed = True
                curr_list.remove(user.id)

        if removed:
            await ctx.send(_("User has been removed from whitelist."))
        else:
            await ctx.send(_("User was not in the whitelist."))

    @whitelist.command(name="clear")
    async def whitelist_clear(self, ctx: commands.Context):
        """
        Clears the whitelist.
        """
        await ctx.bot.db.whitelist.set([])
        await ctx.send(_("Whitelist has been cleared."))

    @commands.group()
    @checks.is_owner()
    async def blacklist(self, ctx: commands.Context):
        """
        Blacklist management commands.
        """
        pass

    @blacklist.command(name="add")
    async def blacklist_add(self, ctx: commands.Context, *, user: discord.User):
        """
        Adds a user to the blacklist.
        """
        if await ctx.bot.is_owner(user):
            await ctx.send(_("You cannot blacklist an owner!"))
            return

        async with ctx.bot.db.blacklist() as curr_list:
            if user.id not in curr_list:
                curr_list.append(user.id)

        await ctx.send(_("User added to blacklist."))

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx: commands.Context):
        """
        Lists blacklisted users.
        """
        curr_list = await ctx.bot.db.blacklist()

        msg = _("Blacklisted Users:")
        for user in curr_list:
            msg += "\n\t- {}".format(user)

        for page in pagify(msg):
            await ctx.send(box(page))

    @blacklist.command(name="remove")
    async def blacklist_remove(self, ctx: commands.Context, *, user: discord.User):
        """
        Removes user from blacklist.
        """
        removed = False

        async with ctx.bot.db.blacklist() as curr_list:
            if user.id in curr_list:
                removed = True
                curr_list.remove(user.id)

        if removed:
            await ctx.send(_("User has been removed from blacklist."))
        else:
            await ctx.send(_("User was not in the blacklist."))

    @blacklist.command(name="clear")
    async def blacklist_clear(self, ctx: commands.Context):
        """
        Clears the blacklist.
        """
        await ctx.bot.db.blacklist.set([])
        await ctx.send(_("Blacklist has been cleared."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def localwhitelist(self, ctx: commands.Context):
        """
        Whitelist management commands.
        """
        pass

    @localwhitelist.command(name="add")
    async def localwhitelist_add(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Adds a user or role to the whitelist.
        """
        user = isinstance(user_or_role, discord.Member)
        async with ctx.bot.db.guild(ctx.guild).whitelist() as curr_list:
            if user_or_role.id not in curr_list:
                curr_list.append(user_or_role.id)

        if user:
            await ctx.send(_("User added to whitelist."))
        else:
            await ctx.send(_("Role added to whitelist."))

    @localwhitelist.command(name="list")
    async def localwhitelist_list(self, ctx: commands.Context):
        """
        Lists whitelisted users and roles.
        """
        curr_list = await ctx.bot.db.guild(ctx.guild).whitelist()

        msg = _("Whitelisted Users and roles:")
        for obj in curr_list:
            msg += "\n\t- {}".format(obj)

        for page in pagify(msg):
            await ctx.send(box(page))

    @localwhitelist.command(name="remove")
    async def localwhitelist_remove(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Removes user or role from whitelist.
        """
        user = isinstance(user_or_role, discord.Member)

        removed = False
        async with ctx.bot.db.guild(ctx.guild).whitelist() as curr_list:
            if user_or_role.id in curr_list:
                removed = True
                curr_list.remove(user_or_role.id)

        if removed:
            if user:
                await ctx.send(_("User has been removed from whitelist."))
            else:
                await ctx.send(_("Role has been removed from whitelist."))
        else:
            if user:
                await ctx.send(_("User was not in the whitelist."))
            else:
                await ctx.send(_("Role was not in the whitelist."))

    @localwhitelist.command(name="clear")
    async def localwhitelist_clear(self, ctx: commands.Context):
        """
        Clears the whitelist.
        """
        await ctx.bot.db.guild(ctx.guild).whitelist.set([])
        await ctx.send(_("Whitelist has been cleared."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    async def localblacklist(self, ctx: commands.Context):
        """
        blacklist management commands.
        """
        pass

    @localblacklist.command(name="add")
    async def localblacklist_add(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Adds a user or role to the blacklist.
        """
        user = isinstance(user_or_role, discord.Member)

        if user and await ctx.bot.is_owner(obj):
            await ctx.send(_("You cannot blacklist an owner!"))
            return

        async with ctx.bot.db.guild(ctx.guild).blacklist() as curr_list:
            if user_or_role.id not in curr_list:
                curr_list.append(user_or_role.id)

        if user:
            await ctx.send(_("User added to blacklist."))
        else:
            await ctx.send(_("Role added to blacklist."))

    @localblacklist.command(name="list")
    async def localblacklist_list(self, ctx: commands.Context):
        """
        Lists blacklisted users and roles.
        """
        curr_list = await ctx.bot.db.guild(ctx.guild).blacklist()

        msg = _("Blacklisted Users and Roles:")
        for obj in curr_list:
            msg += "\n\t- {}".format(obj)

        for page in pagify(msg):
            await ctx.send(box(page))

    @localblacklist.command(name="remove")
    async def localblacklist_remove(
        self, ctx: commands.Context, *, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Removes user or role from blacklist.
        """
        removed = False
        user = isinstance(user_or_role, discord.Member)

        async with ctx.bot.db.guild(ctx.guild).blacklist() as curr_list:
            if user_or_role.id in curr_list:
                removed = True
                curr_list.remove(user_or_role.id)

        if removed:
            if user:
                await ctx.send(_("User has been removed from blacklist."))
            else:
                await ctx.send(_("Role has been removed from blacklist."))
        else:
            if user:
                await ctx.send(_("User was not in the blacklist."))
            else:
                await ctx.send(_("Role was not in the blacklist."))

    @localblacklist.command(name="clear")
    async def localblacklist_clear(self, ctx: commands.Context):
        """
        Clears the blacklist.
        """
        await ctx.bot.db.guild(ctx.guild).blacklist.set([])
        await ctx.send(_("Blacklist has been cleared."))

    @checks.guildowner_or_permissions(administrator=True)
    @commands.group(name="command")
    async def command_manager(self, ctx: commands.Context):
        """Manage the bot's commands."""
        pass

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

        async with ctx.bot.db.disabled_commands() as disabled_commands:
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

        async with ctx.bot.db.guild(ctx.guild).disabled_commands() as disabled_commands:
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

        async with ctx.bot.db.disabled_commands() as disabled_commands:
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

        async with ctx.bot.db.guild(ctx.guild).disabled_commands() as disabled_commands:
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
        await ctx.bot.db.disabled_command_msg.set(message)
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
        ai_ids = await ctx.bot.db.guild(ctx.guild).autoimmune_ids()

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
        async with ctx.bot.db.guild(ctx.guild).autoimmune_ids() as ai_ids:
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
        async with ctx.bot.db.guild(ctx.guild).autoimmune_ids() as ai_ids:
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

    # RPC handlers
    async def rpc_load(self, request):
        cog_name = request.params[0]

        spec = await self.bot.cog_mgr.find_cog(cog_name)
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
