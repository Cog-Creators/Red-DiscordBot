import discord
import traceback
import datetime
import logging
from discord.ext import commands
from core.utils.chat_formatting import inline
from core.sentry_setup import should_log

log = logging.getLogger("red")
sentry_log = logging.getLogger("red.sentry")

INTRO = ("{0}===================\n"
         "{0} Red - Discord Bot \n"
         "{0}===================\n"
         "".format(" " * 20))


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

        print(INTRO)

        if cli_flags.no_cogs is False:
            print("Loading packages...")
            failed = []
            packages = bot.db.packages()

            for package in packages:
                try:
                    spec = bot.cog_mgr.find_cog(package)
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

        if guilds:
            print("Ready and operational on {} servers with a total of {} "
                  "users.".format(guilds, users))
        else:
            print("Ready. I'm not in any server yet!")

        if invite_url:
            print("\nInvite URL: {}\n".format(invite_url))

    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await bot.send_cmd_help(ctx)
        elif isinstance(error, commands.BadArgument):
            await bot.send_cmd_help(ctx)
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
