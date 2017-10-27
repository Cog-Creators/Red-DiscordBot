import datetime
import logging
import pkg_resources
import traceback
from pkg_resources import DistributionNotFound


import discord
from .sentry_setup import should_log
from discord.ext import commands

from .data_manager import storage_type
from .utils.chat_formatting import inline, bordered
from colorama import Fore, Style

log = logging.getLogger("red")
sentry_log = logging.getLogger("red.sentry")

INTRO = """
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
        if bot.uptime is None:
            print("Connected to Discord. Getting ready...")

    @bot.event
    async def on_ready():
        if bot.uptime is not None:
            return

        bot.uptime = datetime.datetime.utcnow()

        if cli_flags.no_cogs is False:
            print("Loading packages...")
            failed = []
            packages = await bot.db.packages()

            for package in packages:
                try:
                    spec = await bot.cog_mgr.find_cog(package)
                    bot.load_extension(spec)
                except Exception as e:
                    log.exception("Failed to load package {}".format(package),
                                  exc_info=e)
                    await bot.remove_loaded_package(package)
            if packages:
                print("Loaded packages: " + ", ".join(packages))

        guilds = len(bot.guilds)
        users = len(set([m for m in bot.get_all_members()]))

        try:
            data = await bot.application_info()
            invite_url = discord.utils.oauth_url(data.id)
        except:
            if bot.user.bot:
                invite_url = "Could not fetch invite url"
            else:
                invite_url = None

        prefixes = await bot.db.prefix()
        lang = await bot.db.locale()
        red_pkg = pkg_resources.get_distribution('Red_DiscordBot')
        dpy_version = pkg_resources.get_distribution('discord.py').version

        INFO = [str(bot.user), "Prefixes: {}".format(', '.join(prefixes)),
                'Language: {}'.format(lang),
                "Red Bot Version: {}".format(red_pkg.version),
                "Discord.py Version: {}".format(dpy_version),
                "Shards: {}".format(bot.shard_count)]

        if guilds:
            INFO.extend(("Servers: {}".format(guilds), "Users: {}".format(users)))
        else:
            print("Ready. I'm not in any server yet!")

        INFO.append('{} cogs with {} commands'.format(len(bot.cogs), len(bot.commands)))

        INFO2 = []

        sentry = await bot.db.enable_sentry()
        voice_reqs = [x.name for x in red_pkg._dep_map['voice']]
        docs_reqs = [x.name for x in red_pkg._dep_map['docs']]
        test_reqs = [x.name for x in red_pkg._dep_map['test']]

        if sentry:
            INFO2.append("√ Report Errors")
        else:
            INFO2.append("X Report Errors")

        if storage_type() == "JSON":
            INFO2.append("X MongoDB")
        else:
            INFO2.append("√ MongoDB")

        try:
            pkg_resources.require(voice_reqs)
        except DistributionNotFound:
            INFO2.append("X Voice")
        else:
            INFO2.append("√ Voice")

        try:
            pkg_resources.require(docs_reqs)
            pkg_resources.require(test_reqs)
        except DistributionNotFound:
            INFO2.append("X Tests and Docs")
        else:
            INFO2.append("√ Tests and Docs")

        print(Fore.RED + INTRO)
        print(Style.RESET_ALL)
        print(bordered(INFO, INFO2))

        if invite_url:
            print("\nInvite URL: {}\n".format(invite_url))

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help()
        elif isinstance(error, commands.BadArgument):
            await ctx.send_help()
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("That command is disabled.")
        elif isinstance(error, commands.CommandInvokeError):
            # Need to test if the following still works
            """
            no_dms = "Cannot send messages to this user"
            is_help_cmd = ctx.command.qualified_name == "help"
            is_forbidden = isinstance(error.original, discord.Forbidden)
            if is_help_cmd and is_forbidden and error.original.text == no_dms:
                msg = ("I couldn't send the help message to you in DM. Either"
                       " you blocked me or you disabled DMs in this server.")
                await ctx.send(msg)
                return
            """
            log.exception("Exception in command '{}'"
                          "".format(ctx.command.qualified_name),
                          exc_info=error.original)
            message = ("Error in command '{}'. Check your console or "
                       "logs for details."
                       "".format(ctx.command.qualified_name))
            exception_log = ("Exception in command '{}'\n"
                             "".format(ctx.command.qualified_name))
            exception_log += "".join(traceback.format_exception(type(error),
                                     error, error.__traceback__))
            bot._last_exception = exception_log
            await ctx.send(inline(message))

            module = ctx.command.module
            if should_log(module):
                sentry_log.exception("Exception in command '{}'"
                                     "".format(ctx.command.qualified_name),
                                     exc_info=error.original)
        elif isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("⛔ You are not authorized to issue that command.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("That command is not available in DMs.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send("This command is on cooldown. "
                           "Try again in {:.2f}s"
                           "".format(error.retry_after))
        else:
            log.exception(type(error).__name__, exc_info=error)

    @bot.event
    async def on_message(message):
        bot.counter["messages_read"] += 1
        await bot.process_commands(message)

    @bot.event
    async def on_resumed():
        bot.counter["sessions_resumed"] += 1

    @bot.event
    async def on_command(command):
        bot.counter["processed_commands"] += 1
