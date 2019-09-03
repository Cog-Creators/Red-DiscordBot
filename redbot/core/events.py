import asyncio
import codecs
import contextlib
import datetime
import logging
import sys
import traceback
from datetime import timedelta

import aiohttp
import discord
import pkg_resources
from colorama import Fore, Style, init
from pkg_resources import DistributionNotFound

from redbot.core.commands import RedHelpFormatter
from . import commands
from .config import get_latest_confs
from .data_manager import storage_type
from .utils import format_fuzzy_results, fuzzy_command_search
from .utils.chat_formatting import bordered, format_perms_list, humanize_timedelta, inline
from .. import VersionInfo, __version__ as red_version, version_info as red_version_info

log = logging.getLogger("red")
init()

INTRO = r"""
______         _           ______ _                       _  ______       _
| ___ \       | |          |  _  (_)                     | | | ___ \     | |
| |_/ /___  __| |  ______  | | | |_ ___  ___ ___  _ __ __| | | |_/ / ___ | |_
|    // _ \/ _` | |______| | | | | / __|/ __/ _ \| '__/ _` | | ___ \/ _ \| __|
| |\ \  __/ (_| |          | |/ /| \__ \ (_| (_) | | | (_| | | |_/ / (_) | |_
\_| \_\___|\__,_|          |___/ |_|___/\___\___/|_|  \__,_| \____/ \___/ \__|
"""


def init_events(bot, cli_flags):
    @bot.event
    async def on_connect():
        # noinspection PyProtectedMember
        if bot._uptime is None:
            print("Connected to Discord. Getting ready...")

    @bot.event
    async def on_ready():
        # noinspection PyProtectedMember
        if bot._uptime is not None:
            return

        bot._uptime = datetime.datetime.utcnow()
        packages = []

        if cli_flags.no_cogs is False:
            # noinspection PyProtectedMember
            packages.extend(await bot._config.packages())

        if cli_flags.load_cogs:
            packages.extend(cli_flags.load_cogs)

        if packages:
            # Load permissions first, for security reasons
            try:
                packages.remove("permissions")
            except ValueError:
                pass
            else:
                packages.insert(0, "permissions")

            to_remove = []
            print("Loading packages...")
            for package in packages:
                try:
                    spec = await bot.cog_mgr.find_cog(package)
                    await bot.load_extension(spec)
                except Exception as e:
                    log.exception("Failed to load package {}".format(package), exc_info=e)
                    await bot.remove_loaded_package(package)
                    to_remove.append(package)
            for package in to_remove:
                packages.remove(package)
            if packages:
                print("Loaded packages: " + ", ".join(packages))

        if bot.rpc_enabled:
            await bot.rpc.initialize()

        guilds = len(bot.guilds)
        users = len(set([m for m in bot.get_all_members()]))

        try:
            data = await bot.application_info()
            invite_url = discord.utils.oauth_url(data.id)
        except Exception:
            invite_url = "Could not fetch invite url"

        # noinspection PyProtectedMember
        prefixes = cli_flags.prefix or (await bot._config.prefix())
        # noinspection PyProtectedMember
        lang = await bot._config.locale()
        red_pkg = pkg_resources.get_distribution("Red-DiscordBot")
        dpy_version = discord.__version__

        info1 = [
            str(bot.user),
            "Prefixes: {}".format(", ".join(prefixes)),
            "Language: {}".format(lang),
            "Red Bot Version: {}".format(red_version),
            "Discord.py Version: {}".format(dpy_version),
            "Shards: {}".format(bot.shard_count),
        ]

        if guilds:
            info1.extend(("Servers: {}".format(guilds), "Users: {}".format(users)))
        else:
            print("Ready. I'm not in any server yet!")

        info1.append("{} cogs with {} commands".format(len(bot.cogs), len(bot.commands)))

        with contextlib.suppress(aiohttp.ClientError, discord.HTTPException):
            async with aiohttp.ClientSession() as session:
                async with session.get("https://pypi.python.org/pypi/red-discordbot/json") as r:
                    data = await r.json()
            if VersionInfo.from_str(data["info"]["version"]) > red_version_info:
                info1.append(
                    "Outdated version! {} is available "
                    "but you're using {}".format(data["info"]["version"], red_version)
                )

                await bot.send_to_owners(
                    "Your Red instance is out of date! {} is the current "
                    "version, however you are using {}!".format(
                        data["info"]["version"], red_version
                    )
                )
        info2 = []

        mongo_enabled = storage_type() != "JSON"
        reqs_installed = {"docs": None, "test": None}
        for key in reqs_installed.keys():
            # noinspection PyProtectedMember
            reqs = [x.name for x in red_pkg._dep_map[key]]
            try:
                pkg_resources.require(reqs)
            except DistributionNotFound:
                reqs_installed[key] = False
            else:
                reqs_installed[key] = True

        options = (
            ("MongoDB", mongo_enabled),
            ("Voice", True),
            ("Docs", reqs_installed["docs"]),
            ("Tests", reqs_installed["test"]),
        )

        on_symbol, off_symbol, ascii_border = _get_startup_screen_specs()

        for option, enabled in options:
            enabled = on_symbol if enabled else off_symbol
            info2.append("{} {}".format(enabled, option))

        print(Fore.RED + INTRO)
        print(Style.RESET_ALL)
        print(bordered(info1, info2, ascii_border=ascii_border))

        if invite_url:
            print("\nInvite URL: {}\n".format(invite_url))

        # noinspection PyProtectedMember
        bot._color = discord.Colour(await bot._config.color())

    @bot.event
    async def on_command_error(ctx, error, unhandled_by_cog=False):

        if not unhandled_by_cog:
            if hasattr(ctx.command, "on_error"):
                return

            if ctx.cog:
                # noinspection PyProtectedMember
                if commands.Cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
                    return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help()
        elif isinstance(error, commands.ConversionFailure):
            if error.args:
                await ctx.send(error.args[0])
            else:
                await ctx.send_help()
        elif isinstance(error, commands.UserInputError):
            await ctx.send_help()
        elif isinstance(error, commands.DisabledCommand):
            # noinspection PyProtectedMember
            disabled_message = await bot._config.disabled_command_msg()
            if disabled_message:
                await ctx.send(disabled_message.replace("{command}", ctx.invoked_with))
        elif isinstance(error, commands.CommandInvokeError):
            log.exception(
                "Exception in command '{}'".format(ctx.command.qualified_name),
                exc_info=error.original,
            )

            message = "Error in command '{}'. Check your console or logs for details.".format(
                ctx.command.qualified_name
            )
            exception_log = "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            bot._last_exception = exception_log
            await ctx.send(inline(message))
        elif isinstance(error, commands.CommandNotFound):
            fuzzy_commands = await fuzzy_command_search(
                ctx,
                commands={
                    c async for c in RedHelpFormatter.help_filter_func(ctx, bot.walk_commands())
                },
            )
            if not fuzzy_commands:
                pass
            elif await ctx.embed_requested():
                await ctx.send(embed=await format_fuzzy_results(ctx, fuzzy_commands, embed=True))
            else:
                await ctx.send(await format_fuzzy_results(ctx, fuzzy_commands, embed=False))
        elif isinstance(error, commands.BotMissingPermissions):
            if bin(error.missing.value).count("1") == 1:  # Only one perm missing
                plural = ""
            else:
                plural = "s"
            await ctx.send(
                "I require the {perms} permission{plural} to execute that command.".format(
                    perms=format_perms_list(error.missing), plural=plural
                )
            )
        elif isinstance(error, commands.UserFeedbackCheckFailure):
            if error.message:
                await ctx.send(error.message)
        elif isinstance(error, commands.CheckFailure):
            pass
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("That command is not available in DMs.")
        elif isinstance(error, commands.CommandOnCooldown):
            if error.retry_after < 1:
                async with ctx.typing():
                    # the sleep here is so that commands using this for ratelimit purposes
                    # are not made more lenient than intended, while still being
                    # more convenient for the user than redoing it less than a second later.
                    await asyncio.sleep(error.retry_after)
                    await ctx.bot.invoke(ctx)
                    # done this way so checks still occur if there are other
                    # failures possible than just cooldown.
                    # do not change to ctx.reinvoke()
                    return

            await ctx.send(
                "This command is on cooldown. Try again in {}.".format(
                    humanize_timedelta(seconds=error.retry_after)
                ),
                delete_after=error.retry_after,
            )
        else:
            log.exception(type(error).__name__, exc_info=error)

    @bot.event
    async def on_message(message):
        # noinspection PyProtectedMember
        bot._counter["messages_read"] += 1
        await bot.process_commands(message)
        discord_now = message.created_at
        # noinspection PyProtectedMember,PyProtectedMember
        if (
            not bot._checked_time_accuracy
            or (discord_now - timedelta(minutes=60)) > bot._checked_time_accuracy
        ):
            system_now = datetime.datetime.utcnow()
            diff = abs((discord_now - system_now).total_seconds())
            if diff > 60:
                log.warning(
                    "Detected significant difference (%d seconds) in system clock to discord's "
                    "clock. Any time sensitive code may fail.",
                    diff,
                )
            bot._checked_time_accuracy = discord_now

    @bot.event
    async def on_resumed():
        # noinspection PyProtectedMember
        bot._counter["sessions_resumed"] += 1

    @bot.event
    async def on_command(command):
        # noinspection PyProtectedMember
        bot._counter["processed_commands"] += 1

    @bot.event
    async def on_command_add(command: commands.Command):
        # noinspection PyProtectedMember
        disabled_commands = await bot._config.disabled_commands()
        if command.qualified_name in disabled_commands:
            command.enabled = False
        for guild in bot.guilds:
            # noinspection PyProtectedMember
            disabled_commands = await bot._config.guild(guild).disabled_commands()
            if command.qualified_name in disabled_commands:
                command.disable_in(guild)

    async def _guild_added(guild: discord.Guild):
        # noinspection PyProtectedMember
        disabled_commands = await bot._config.guild(guild).disabled_commands()
        for command_name in disabled_commands:
            command_obj = bot.get_command(command_name)
            if command_obj is not None:
                command_obj.disable_in(guild)

    @bot.event
    async def on_guild_join(guild: discord.Guild):
        await _guild_added(guild)

    @bot.event
    async def on_guild_available(guild: discord.Guild):
        # We need to check guild-disabled commands here since some cogs
        # are loaded prior to `on_ready`.
        await _guild_added(guild)

    @bot.event
    async def on_guild_leave(guild: discord.Guild):
        # Clean up any unneeded checks
        # noinspection PyProtectedMember
        disabled_commands = await bot._config.guild(guild).disabled_commands()
        for command_name in disabled_commands:
            command_obj = bot.get_command(command_name)
            if command_obj is not None:
                command_obj.enable_in(guild)

    @bot.event
    async def on_cog_add(cog: commands.Cog):
        confs = get_latest_confs()
        for c in confs:
            uuid = c.unique_identifier
            group_data = c.custom_groups
            # noinspection PyProtectedMember
            await bot._config.custom("CUSTOM_GROUPS", c.cog_name, uuid).set(group_data)


def _get_startup_screen_specs():
    """Get specs for displaying the startup screen on stdout.

    This is so we don't get encoding errors when trying to print unicode
    emojis to stdout (particularly with Windows Command Prompt).

    Returns
    -------
    `tuple`
        Tuple in the form (`str`, `str`, `bool`) containing (in order) the
        on symbol, off symbol and whether or not the border should be pure ascii.

    """
    encoder = codecs.getencoder(sys.stdout.encoding)
    check_mark = "\N{SQUARE ROOT}"
    try:
        encoder(check_mark)
    except UnicodeEncodeError:
        on_symbol = "[X]"
        off_symbol = "[ ]"
    else:
        on_symbol = check_mark
        off_symbol = "X"

    try:
        encoder("┌┐└┘─│")  # border symbols
    except UnicodeEncodeError:
        ascii_border = True
    else:
        ascii_border = False

    return on_symbol, off_symbol, ascii_border
