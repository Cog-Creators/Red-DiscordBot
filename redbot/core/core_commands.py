import asyncio
import datetime
import importlib
import itertools
import json
import logging
import os
import sys
import tarfile
import traceback
from collections import namedtuple
from pathlib import Path
from random import SystemRandom
from string import ascii_letters, digits
from distutils.version import StrictVersion

import aiohttp
import discord
import pkg_resources

from redbot.core import __version__
from redbot.core import checks
from redbot.core import i18n
from redbot.core import rpc
from redbot.core import commands
from .utils import TYPE_CHECKING
from .utils.chat_formatting import pagify, box, inline

if TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["Core"]

log = logging.getLogger("red")

OWNER_DISCLAIMER = (
    "⚠ **Only** the person who is hosting Red should be "
    "owner. **This has SERIOUS security implications. The "
    "owner can access any data that is present on the host "
    "system.** ⚠"
)


_ = i18n.Translator("Core", __file__)


@i18n.cog_i18n(_)
class Core:
    """Commands related to core functions"""

    def __init__(self, bot):
        self.bot = bot  # type: Red

        rpc.add_method("core", self.rpc_load)
        rpc.add_method("core", self.rpc_unload)
        rpc.add_method("core", self.rpc_reload)

    @commands.command(hidden=True)
    async def ping(self, ctx):
        """Pong."""
        if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).add_reactions:
            await ctx.message.add_reaction("\U0001f3d3")  # ping pong paddle
        else:
            await ctx.maybe_send_embed("Pong.")

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

        async with aiohttp.ClientSession() as session:
            async with session.get("{}/json".format(red_pypi)) as r:
                data = await r.json()
        outdated = StrictVersion(data["info"]["version"]) > StrictVersion(__version__)
        about = (
            "This is an instance of [Red, an open source Discord bot]({}) "
            "created by [Twentysix]({}) and [improved by many]({}).\n\n"
            "Red is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({}) "
            "and help us improve!\n\n"
            "".format(red_repo, author_repo, org_repo, support_server_url)
        )

        embed = discord.Embed(color=discord.Color.red())
        embed.add_field(name="Instance owned by", value=str(owner))
        embed.add_field(name="Python", value=python_version)
        embed.add_field(name="discord.py", value=dpy_version)
        embed.add_field(name="Red version", value=red_version)
        if outdated:
            embed.add_field(
                name="Outdated", value="Yes, {} is available".format(data["info"]["version"])
            )
        embed.add_field(name="About Red", value=about, inline=False)

        embed.set_footer(
            text="Bringing joy since 02 Jan 2016 (over " "{} days ago!)".format(days_since)
        )
        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            await ctx.send("I need the `Embed links` permission to send this")

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows Red's uptime"""
        since = ctx.bot.uptime.strftime("%Y-%m-%d %H:%M:%S")
        passed = self.get_bot_uptime()
        await ctx.send("Been up for: **{}** (since {} UTC)".format(passed, since))

    def get_bot_uptime(self, *, brief=False):
        # Courtesy of Danny
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = "{d} days, {h} hours, {m} minutes, and {s} seconds"
            else:
                fmt = "{h} hours, {m} minutes, and {s} seconds"
        else:
            fmt = "{h}h {m}m {s}s"
            if days:
                fmt = "{d}d " + fmt

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
            text = "Embed settings:\n\n"
            global_default = await self.bot.db.embeds()
            text += "Global default: {}\n".format(global_default)
            if ctx.guild:
                guild_setting = await self.bot.db.guild(ctx.guild).embeds()
                text += "Guild setting: {}\n".format(guild_setting)
            user_setting = await self.bot.db.user(ctx.author).embeds()
            text += "User setting: {}".format(user_setting)
            await ctx.send(box(text))
            await ctx.send_help()

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
            _("Embeds are now {} by default.").format("disabled" if current else "enabled")
        )

    @embedset.command(name="guild")
    @checks.guildowner_or_permissions(administrator=True)
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
                _("Embeds are now {} for this guild.").format("enabled" if enabled else "disabled")
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
                _("Embeds are now {} for you.").format("enabled" if enabled else "disabled")
            )

    @commands.command()
    @checks.is_owner()
    async def traceback(self, ctx, public: bool = False):
        """Sends to the owner the last command exception that has occurred

        If public (yes is specified), it will be sent to the chat instead"""
        if not public:
            destination = ctx.author
        else:
            destination = ctx.channel

        if self.bot._last_exception:
            for page in pagify(self.bot._last_exception):
                await destination.send(box(page, lang="py"))
        else:
            await ctx.send("No exception has occurred yet")

    @commands.command()
    @checks.is_owner()
    async def invite(self, ctx):
        """Show's Red's invite url"""
        if self.bot.user.bot:
            app_info = await self.bot.application_info()
            await ctx.author.send(discord.utils.oauth_url(app_info.id))
        else:
            await ctx.send("I'm not a bot account. I have no invite URL.")

    @commands.command()
    @commands.guild_only()
    @checks.is_owner()
    async def leave(self, ctx):
        """Leaves server"""
        author = ctx.author
        guild = ctx.guild

        await ctx.send("Are you sure you want me to leave this server?" " Type yes to confirm.")

        def conf_check(m):
            return m.author == author

        response = await self.bot.wait_for("message", check=conf_check)

        if response.content.lower().strip() == "yes":
            await ctx.send("Alright. Bye :wave:")
            log.debug("Leaving '{}'".format(guild.name))
            await guild.leave()

    @commands.command()
    @checks.is_owner()
    async def servers(self, ctx):
        """Lists and allows to leave servers"""
        owner = ctx.author
        guilds = sorted(list(self.bot.guilds), key=lambda s: s.name.lower())
        msg = ""
        for i, server in enumerate(guilds, 1):
            msg += "{}: {}\n".format(i, server.name)

        msg += "\nTo leave a server, just type its number."

        for page in pagify(msg, ["\n"]):
            await ctx.send(page)

        def msg_check(m):
            return m.author == owner

        while msg is not None:
            try:
                msg = await self.bot.wait_for("message", check=msg_check, timeout=15)
            except asyncio.TimeoutError:
                await ctx.send("I guess not.")
                break
            try:
                msg = int(msg.content) - 1
                if msg < 0:
                    break
                await self.leave_confirmation(guilds[msg], owner, ctx)
                break
            except (IndexError, ValueError, AttributeError):
                pass

    async def leave_confirmation(self, server, owner, ctx):
        await ctx.send("Are you sure you want me to leave {}? (yes/no)".format(server.name))

        def conf_check(m):
            return m.author == owner

        try:
            msg = await self.bot.wait_for("message", check=conf_check, timeout=15)
            if msg.content.lower().strip() in ("yes", "y"):
                if server.owner == ctx.bot.user:
                    await ctx.send("I cannot leave a guild I am the owner of.")
                    return
                await server.leave()
                if server != ctx.guild:
                    await ctx.send("Done.")
            else:
                await ctx.send("Alright then.")
        except asyncio.TimeoutError:
            await ctx.send("I guess not.")

    @commands.command()
    @checks.is_owner()
    async def load(self, ctx, *, cog_name: str):
        """Loads packages"""

        failed_packages = []
        loaded_packages = []
        notfound_packages = []

        cognames = [c.strip() for c in cog_name.split(" ")]
        cogspecs = []

        for c in cognames:
            try:
                spec = await ctx.bot.cog_mgr.find_cog(c)
                cogspecs.append((spec, c))
            except RuntimeError:
                notfound_packages.append(inline(c))
                # await ctx.send(_("No module named '{}' was found in any"
                #                 " cog path.").format(c))

        if len(cogspecs) > 0:
            for spec, name in cogspecs:
                try:
                    await ctx.bot.load_extension(spec)
                except Exception as e:
                    log.exception("Package loading failed", exc_info=e)

                    exception_log = (
                        "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
                    )
                    exception_log += "".join(
                        traceback.format_exception(type(e), e, e.__traceback__)
                    )
                    self.bot._last_exception = exception_log
                    failed_packages.append(inline(name))
                else:
                    await ctx.bot.add_loaded_package(name)
                    loaded_packages.append(inline(name))

        if loaded_packages:
            fmt = "Loaded {packs}"
            formed = self.get_package_strings(loaded_packages, fmt)
            await ctx.send(_(formed))

        if failed_packages:
            fmt = (
                "Failed to load package{plural} {packs}. Check your console or "
                "logs for details."
            )
            formed = self.get_package_strings(failed_packages, fmt)
            await ctx.send(_(formed))

        if notfound_packages:
            fmt = "The package{plural} {packs} {other} not found in any cog path."
            formed = self.get_package_strings(notfound_packages, fmt, ("was", "were"))
            await ctx.send(_(formed))

    @commands.group()
    @checks.is_owner()
    async def unload(self, ctx, *, cog_name: str):
        """Unloads packages"""
        cognames = [c.strip() for c in cog_name.split(" ")]
        failed_packages = []
        unloaded_packages = []

        for c in cognames:
            if c in ctx.bot.extensions:
                ctx.bot.unload_extension(c)
                await ctx.bot.remove_loaded_package(c)
                unloaded_packages.append(inline(c))
            else:
                failed_packages.append(inline(c))

        if unloaded_packages:
            fmt = "Package{plural} {packs} {other} unloaded."
            formed = self.get_package_strings(unloaded_packages, fmt, ("was", "were"))
            await ctx.send(_(formed))

        if failed_packages:
            fmt = "The package{plural} {packs} {other} not loaded."
            formed = self.get_package_strings(failed_packages, fmt, ("is", "are"))
            await ctx.send(_(formed))

    @commands.command(name="reload")
    @checks.is_owner()
    async def _reload(self, ctx, *, cog_name: str):
        """Reloads packages"""

        cognames = [c.strip() for c in cog_name.split(" ")]

        for c in cognames:
            ctx.bot.unload_extension(c)

        cogspecs = []
        failed_packages = []
        loaded_packages = []
        notfound_packages = []

        for c in cognames:
            try:
                spec = await ctx.bot.cog_mgr.find_cog(c)
                cogspecs.append((spec, c))
            except RuntimeError:
                notfound_packages.append(inline(c))

        for spec, name in cogspecs:
            try:
                self.cleanup_and_refresh_modules(spec.name)
                await ctx.bot.load_extension(spec)
                loaded_packages.append(inline(name))
            except Exception as e:
                log.exception("Package reloading failed", exc_info=e)

                exception_log = (
                    "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
                )
                exception_log += "".join(traceback.format_exception(type(e), e, e.__traceback__))
                self.bot._last_exception = exception_log

                failed_packages.append(inline(name))

        if loaded_packages:
            fmt = "Package{plural} {packs} {other} reloaded."
            formed = self.get_package_strings(loaded_packages, fmt, ("was", "were"))
            await ctx.send(_(formed))

        if failed_packages:
            fmt = ("Failed to reload package{plural} {packs}. Check your " "logs for details")
            formed = self.get_package_strings(failed_packages, fmt)
            await ctx.send(_(formed))

        if notfound_packages:
            fmt = "The package{plural} {packs} {other} not found in any cog path."
            formed = self.get_package_strings(notfound_packages, fmt, ("was", "were"))
            await ctx.send(_(formed))

    def get_package_strings(self, packages: list, fmt: str, other: tuple = None):
        """
        Gets the strings needed for the load, unload and reload commands
        """
        if other is None:
            other = ("", "")
        plural = "s" if len(packages) > 1 else ""
        use_and, other = ("", other[0]) if len(packages) == 1 else (" and ", other[1])
        packages_string = ", ".join(packages[:-1]) + use_and + packages[-1]

        form = {"plural": plural, "packs": packages_string, "other": other}
        final_string = fmt.format(**form)
        return final_string

    @commands.command(name="shutdown")
    @checks.is_owner()
    async def _shutdown(self, ctx, silently: bool = False):
        """Shuts down the bot"""
        wave = "\N{WAVING HAND SIGN}"
        skin = "\N{EMOJI MODIFIER FITZPATRICK TYPE-3}"
        try:  # We don't want missing perms to stop our shutdown
            if not silently:
                await ctx.send(_("Shutting down... ") + wave + skin)
        except:
            pass
        await ctx.bot.shutdown()

    @commands.command(name="restart")
    @checks.is_owner()
    async def _restart(self, ctx, silently: bool = False):
        """Attempts to restart Red

        Makes Red quit with exit code 26
        The restart is not guaranteed: it must be dealt
        with by the process manager in use"""
        try:
            if not silently:
                await ctx.send(_("Restarting..."))
        except:
            pass
        await ctx.bot.shutdown(restart=True)

    def cleanup_and_refresh_modules(self, module_name: str):
        """Interally reloads modules so that changes are detected"""
        splitted = module_name.split(".")

        def maybe_reload(new_name):
            try:
                lib = sys.modules[new_name]
            except KeyError:
                pass
            else:
                importlib._bootstrap._exec(lib.__spec__, lib)

        modules = itertools.accumulate(splitted, "{}.{}".format)
        for m in modules:
            maybe_reload(m)

        children = {name: lib for name, lib in sys.modules.items() if name.startswith(module_name)}
        for child_name, lib in children.items():
            importlib._bootstrap._exec(lib.__spec__, lib)

    @commands.group(name="set")
    async def _set(self, ctx):
        """Changes Red's settings"""
        if ctx.invoked_subcommand is None:
            admin_role_id = await ctx.bot.db.guild(ctx.guild).admin_role()
            admin_role = discord.utils.get(ctx.guild.roles, id=admin_role_id)
            mod_role_id = await ctx.bot.db.guild(ctx.guild).mod_role()
            mod_role = discord.utils.get(ctx.guild.roles, id=mod_role_id)
            prefixes = await ctx.bot.db.guild(ctx.guild).prefix()
            if not prefixes:
                prefixes = await ctx.bot.db.prefix()
            locale = await ctx.bot.db.locale()

            settings = (
                "{} Settings:\n\n"
                "Prefixes: {}\n"
                "Admin role: {}\n"
                "Mod role: {}\n"
                "Locale: {}"
                "".format(
                    ctx.bot.user.name,
                    " ".join(prefixes),
                    admin_role.name if admin_role else "Not set",
                    mod_role.name if mod_role else "Not set",
                    locale,
                )
            )
            await ctx.send(box(settings))
            await ctx.send_help()

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def adminrole(self, ctx, *, role: discord.Role):
        """Sets the admin role for this server"""
        await ctx.bot.db.guild(ctx.guild).admin_role.set(role.id)
        await ctx.send(_("The admin role for this guild has been set."))

    @_set.command()
    @checks.guildowner()
    @commands.guild_only()
    async def modrole(self, ctx, *, role: discord.Role):
        """Sets the mod role for this server"""
        await ctx.bot.db.guild(ctx.guild).mod_role.set(role.id)
        await ctx.send(_("The mod role for this guild has been set."))

    @_set.command()
    @checks.is_owner()
    async def avatar(self, ctx, url: str):
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
    async def _game(self, ctx, *, game: str = None):
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
    async def _listening(self, ctx, *, listening: str = None):
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
    async def _watching(self, ctx, *, watching: str = None):
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
    async def status(self, ctx, *, status: str):
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
    async def stream(self, ctx, streamer=None, *, stream_title=None):
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
    async def _username(self, ctx, *, username: str):
        """Sets Red's username"""
        try:
            await ctx.bot.user.edit(username=username)
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Failed to change name. Remember that you can "
                    "only do it up to 2 times an hour. Use "
                    "nicknames if you need frequent changes. "
                    "`{}set nickname`"
                ).format(
                    ctx.prefix
                )
            )
        else:
            await ctx.send(_("Done."))

    @_set.command(name="nickname")
    @checks.admin()
    @commands.guild_only()
    async def _nickname(self, ctx, *, nickname: str = None):
        """Sets Red's nickname"""
        try:
            await ctx.guild.me.edit(nick=nickname)
        except discord.Forbidden:
            await ctx.send(_("I lack the permissions to change my own " "nickname."))
        else:
            await ctx.send("Done.")

    @_set.command(aliases=["prefixes"])
    @checks.is_owner()
    async def prefix(self, ctx, *prefixes):
        """Sets Red's global prefix(es)"""
        if not prefixes:
            await ctx.send_help()
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.db.prefix.set(prefixes)
        await ctx.send(_("Prefix set."))

    @_set.command(aliases=["serverprefixes"])
    @checks.admin()
    @commands.guild_only()
    async def serverprefix(self, ctx, *prefixes):
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
    async def owner(self, ctx):
        """Sets Red's main owner"""

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # According to the Python docs this is suitable for cryptographic use
        random = SystemRandom()
        length = random.randint(25, 35)
        chars = ascii_letters + digits
        token = ""

        for i in range(length):
            token += random.choice(chars)
        log.info("{0} ({0.id}) requested to be set as owner." "".format(ctx.author))
        print(_("\nVerification token:"))
        print(token)

        await ctx.send(_("Remember:\n") + OWNER_DISCLAIMER)
        await asyncio.sleep(5)

        await ctx.send(
            _(
                "I have printed a one-time token in the console. "
                "Copy and paste it here to confirm you are the owner."
            )
        )

        try:
            message = await ctx.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            self.owner.reset_cooldown(ctx)
            await ctx.send(_("The set owner request has timed out."))
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
    async def token(self, ctx, token: str):
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
                ).format(
                    self.bot.user.id
                )
            )
            return

        await ctx.bot.db.token.set(token)
        await ctx.send("Token set. Restart me.")

    @_set.command()
    @checks.is_owner()
    async def locale(self, ctx: commands.Context, locale_name: str):
        """
        Changes bot locale.

        Use [p]listlocales to get a list of available locales.

        To reset to English, use "en-US".
        """
        i18n.set_locale(locale_name)

        await ctx.bot.db.locale.set(locale_name)

        await ctx.send(_("Locale has been set."))

    @_set.command()
    @checks.is_owner()
    async def sentry(self, ctx: commands.Context, on_or_off: bool):
        """Enable or disable Sentry logging.

        Sentry is the service Red uses to manage error reporting. This should
        be disabled if you have made your own modifications to the redbot
        package.
        """
        await ctx.bot.db.enable_sentry.set(on_or_off)
        if on_or_off:
            ctx.bot.enable_sentry()
            await ctx.send(_("Done. Sentry logging is now enabled."))
        else:
            ctx.bot.disable_sentry()
            await ctx.send(_("Done. Sentry logging is now disabled."))

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
            locale_list = sorted(set([loc.stem for loc in list(red_path.glob("**/*.po"))]))
            pages = pagify("\n".join(locale_list))

        await ctx.send_interactive(pages, box_lang="Available Locales:")

    @commands.command()
    @checks.is_owner()
    async def backup(self, ctx, backup_path: str = None):
        """Creates a backup of all data for the instance."""
        from redbot.core.data_manager import basic_config, instance_name
        from redbot.core.drivers.red_json import JSON

        data_dir = Path(basic_config["DATA_PATH"])
        if basic_config["STORAGE_TYPE"] == "MongoDB":
            from redbot.core.drivers.red_mongo import Mongo

            m = Mongo("Core", **basic_config["STORAGE_DETAILS"])
            db = m.db
            collection_names = await db.collection_names(include_system_collections=False)
            for c_name in collection_names:
                if c_name == "Core":
                    c_data_path = data_dir / basic_config["CORE_PATH_APPEND"]
                else:
                    c_data_path = data_dir / basic_config["COG_PATH_APPEND"]
                output = {}
                docs = await db[c_name].find().to_list(None)
                for item in docs:
                    item_id = str(item.pop("_id"))
                    output[item_id] = item
                target = JSON(c_name, data_path_override=c_data_path)
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
                for _, repo in repo_mgr._repos:
                    repo_output.append(
                        {{"url": repo.url, "name": repo.name, "branch": repo.branch}}
                    )
                repo_filename = data_dir / "cogs" / "RepoManager" / "repos.json"
                with open(str(repo_filename), "w") as f:
                    f.write(json.dumps(repo_output, indent=4))
            for f in data_dir.glob("**/*"):
                if not any(ex in str(f) for ex in exclusions):
                    to_backup.append(f)
            with tarfile.open(str(backup_file), "w:gz") as tar:
                for f in to_backup:
                    tar.add(str(f), recursive=False)
            await ctx.send(
                _("A backup has been made of this instance. It is at {}.").format(backup_file)
            )
        else:
            await ctx.send(_("That directory doesn't seem to exist..."))

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def contact(self, ctx, *, message: str):
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

        content = _("Use `{}dm {} <text>` to reply to this user" "").format(prefix, author.id)

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
                    _("I cannot send your message, I'm unable to find " "my owner... *sigh*")
                )
            except:
                await ctx.send(_("I'm unable to deliver your message. Sorry."))
            else:
                await ctx.send(_("Your message has been sent."))
        else:
            msg_text = ("{}\nMessage:\n\n{}\n{}".format(description, message, footer))
            try:
                await owner.send("{}\n{}".format(content, box(msg_text)))
            except discord.InvalidArgument:
                await ctx.send(
                    _("I cannot send your message, I'm unable to find " "my owner... *sigh*")
                )
            except:
                await ctx.send(_("I'm unable to deliver your message. Sorry."))
            else:
                await ctx.send(_("Your message has been sent."))

    @commands.command()
    @checks.is_owner()
    async def dm(self, ctx, user_id: int, *, message: str):
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
            except:
                await ctx.send(
                    _("Sorry, I couldn't deliver your message " "to {}").format(destination)
                )
            else:
                await ctx.send(_("Message delivered to {}").format(destination))
        else:
            response = "{}\nMessage:\n\n{}".format(description, message)
            try:
                await destination.send("{}\n{}".format(box(response), content))
            except:
                await ctx.send(
                    _("Sorry, I couldn't deliver your message " "to {}").format(destination)
                )
            else:
                await ctx.send(_("Message delivered to {}").format(destination))

    @commands.group()
    @checks.is_owner()
    async def whitelist(self, ctx):
        """
        Whitelist management commands.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

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
    async def whitelist_list(self, ctx):
        """
        Lists whitelisted users.
        """
        curr_list = await ctx.bot.db.whitelist()

        msg = _("Whitelisted Users:")
        for user in curr_list:
            msg.append("\n\t- {}".format(user))

        for page in pagify(msg):
            await ctx.send(box(page))

    @whitelist.command(name="remove")
    async def whitelist_remove(self, ctx, user: discord.User):
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
    async def whitelist_clear(self, ctx):
        """
        Clears the whitelist.
        """
        await ctx.bot.db.whitelist.set([])
        await ctx.send(_("Whitelist has been cleared."))

    @commands.group()
    @checks.is_owner()
    async def blacklist(self, ctx):
        """
        blacklist management commands.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @blacklist.command(name="add")
    async def blacklist_add(self, ctx, user: discord.User):
        """
        Adds a user to the blacklist.
        """
        if await ctx.bot.is_owner(user):
            ctx.send(_("You cannot blacklist an owner!"))
            return

        async with ctx.bot.db.blacklist() as curr_list:
            if user.id not in curr_list:
                curr_list.append(user.id)

        await ctx.send(_("User added to blacklist."))

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx):
        """
        Lists blacklisted users.
        """
        curr_list = await ctx.bot.db.blacklist()

        msg = _("blacklisted Users:")
        for user in curr_list:
            msg.append("\n\t- {}".format(user))

        for page in pagify(msg):
            await ctx.send(box(page))

    @blacklist.command(name="remove")
    async def blacklist_remove(self, ctx, user: discord.User):
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
    async def blacklist_clear(self, ctx):
        """
        Clears the blacklist.
        """
        await ctx.bot.db.blacklist.set([])
        await ctx.send(_("blacklist has been cleared."))

    # RPC handlers
    async def rpc_load(self, request):
        cog_name = request.params[0]

        spec = await self.bot.cog_mgr.find_cog(cog_name)
        if spec is None:
            raise LookupError("No such cog found.")

        self.cleanup_and_refresh_modules(spec.name)

        self.bot.load_extension(spec)

    async def rpc_unload(self, request):
        cog_name = request.params[0]

        self.bot.unload_extension(cog_name)

    async def rpc_reload(self, request):
        await self.rpc_unload(request)
        await self.rpc_load(request)
