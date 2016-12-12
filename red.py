import asyncio
import os
import sys
import logging
import logging.handlers
import traceback
import datetime

try:
    assert sys.version_info >= (3, 5)
    from discord.ext import commands
    import discord
except ImportError:
    print("Discord.py is not installed.\n"
          "Consult the guide for your operating system "
          "and do ALL the steps in order.\n"
          "https://twentysix26.github.io/Red-Docs/\n")
    sys.exit()
except AssertionError:
    print("Red needs Python 3.5 or superior.\n"
          "Consult the guide for your operating system "
          "and do ALL the steps in order.\n"
          "https://twentysix26.github.io/Red-Docs/\n")
    sys.exit()

from cogs.utils.settings import Settings
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import inline
from collections import Counter
from io import TextIOWrapper

#
# Red, a Discord bot by Twentysix, based on discord.py and its command
#                             extension.
#
#                   https://github.com/Twentysix26/
#
#
# red.py and cogs/utils/checks.py both contain some modified functions
#                     originally made by Rapptz.
#
#                 https://github.com/Rapptz/RoboDanny/
#

description = "Red - A multifunction Discord bot by Twentysix"


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):

        def prefix_manager(bot, message):
            """
            Returns prefixes of the message's server if set.
            If none are set or if the message's server is None
            it will return the global prefixes instead.

            Requires a Bot instance and a Message object to be
            passed as arguments.
            """
            return bot.settings.get_prefixes(message.server)

        self.counter = Counter()
        self.uptime = datetime.datetime.now() #  Will be refreshed before login
        self._message_modifiers = []
        self.settings = Settings()
        self._intro_displayed = False
        kwargs["self_bot"] = self.settings.self_bot
        super().__init__(*args, command_prefix=prefix_manager, **kwargs)

    async def send_message(self, *args, **kwargs):
        if self._message_modifiers:
            if "content" in kwargs:
                pass
            elif len(args) == 2:
                args = list(args)
                kwargs["content"] = args.pop()
            else:
                return await super().send_message(*args, **kwargs)

            content = kwargs['content']
            for m in self._message_modifiers:
                try:
                    content = str(m(content))
                except:   # Faulty modifiers should not
                    pass  # break send_message
            kwargs['content'] = content

        return await super().send_message(*args, **kwargs)

    def add_message_modifier(self, func):
        """
        Adds a message modifier to the bot

        A message modifier is a callable that accepts a message's
        content as the first positional argument.
        Before a message gets sent, func will get called with
        the message's content as the only argument. The message's
        content will then be modified to be the func's return
        value.
        Exceptions thrown by the callable will be catched and
        silenced.
        """
        if not callable(func):
            raise TypeError("The message modifier function "
                            "must be a callable.")

        self._message_modifiers.append(func)

    def remove_message_modifier(self, func):
        """Removes a message modifier from the bot"""
        if func not in self._message_modifiers:
            raise RuntimeError("Function not present in the message "
                               "modifiers.")

        self._message_modifiers.remove(func)

    def clear_message_modifiers(self):
        """Removes all message modifiers from the bot"""
        self._message_modifiers.clear()

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            for page in pages:
                await self.send_message(ctx.message.channel, page)
        else:
            pages = self.formatter.format_help_for(ctx, ctx.command)
            for page in pages:
                await self.send_message(ctx.message.channel, page)

    def user_allowed(self, message):
        author = message.author

        if author.bot:
            return False

        if author == self.user:
            return self.settings.self_bot

        mod = self.get_cog('Mod')

        if mod is not None:
            if settings.owner == author.id:
                return True
            if not message.channel.is_private:
                server = message.server
                names = (settings.get_server_admin(
                    server), settings.get_server_mod(server))
                results = map(
                    lambda name: discord.utils.get(author.roles, name=name),
                    names)
                for r in results:
                    if r is not None:
                        return True

            if author.id in mod.blacklist_list:
                return False

            if mod.whitelist_list:
                if author.id not in mod.whitelist_list:
                    return False

            if not message.channel.is_private:
                if message.server.id in mod.ignore_list["SERVERS"]:
                    return False

                if message.channel.id in mod.ignore_list["CHANNELS"]:
                    return False
            return True
        else:
            return True


class Formatter(commands.HelpFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _add_subcommands_to_page(self, max_width, commands):
        for name, command in sorted(commands, key=lambda t: t[0]):
            if name in command.aliases:
                # skip aliases
                continue

            entry = '  {0:<{width}} {1}'.format(name, command.short_doc,
                                                width=max_width)
            shortened = self.shorten(entry)
            self._paginator.add_line(shortened)


formatter = Formatter(show_check_failure=False)

bot = Bot(formatter=formatter, description=description, pm_help=None)

send_cmd_help = bot.send_cmd_help  # Backwards
user_allowed = bot.user_allowed    # compatibility

settings = bot.settings


@bot.event
async def on_ready():
    if bot._intro_displayed:
        return
    bot._intro_displayed = True

    owner_cog = bot.get_cog('Owner')
    total_cogs = len(owner_cog._list_cogs())
    users = len(set(bot.get_all_members()))
    servers = len(bot.servers)
    channels = len([c for c in bot.get_all_channels()])

    login_time = datetime.datetime.now() - bot.uptime
    login_time = login_time.seconds + login_time.microseconds/1E6

    print("Login successful. ({}ms)\n".format(login_time))

    owner = await set_bot_owner()

    print("-----------------")
    print("Red - Discord Bot")
    print("-----------------")
    print(str(bot.user))
    print("\nConnected to:")
    print("{} servers".format(servers))
    print("{} channels".format(channels))
    print("{} users\n".format(users))
    prefix_label = "Prefixes:" if len(settings.prefixes) > 1 else "Prefix:"
    print("{} {}".format(prefix_label, " ".join(settings.prefixes)))
    print("Owner: " + str(owner))
    print("{}/{} active cogs with {} commands".format(
        len(bot.cogs), total_cogs, len(bot.commands)))
    print("-----------------")

    if settings.token and not settings.self_bot:
        print("\nUse this url to bring your bot to a server:")
        url = await get_oauth_url()
        bot.oauth_url = url
        print(url)

    print("\nOfficial server: https://discord.me/Red-DiscordBot")

    if os.name == "nt" and os.path.isfile("update.bat"):
        print("\nMake sure to keep your bot updated by running the file "
              "update.bat")
    else:
        print("\nMake sure to keep your bot updated by using: git pull")
        print("and: pip3 install -U git+https://github.com/Rapptz/"
              "discord.py@master#egg=discord.py[voice]")

    await bot.get_cog('Owner').disable_commands()


@bot.event
async def on_resumed():
    bot.counter["session_resumed"] += 1


@bot.event
async def on_command(command, ctx):
    bot.counter["processed_commands"] += 1


@bot.event
async def on_message(message):
    bot.counter["messages_read"] += 1
    if user_allowed(message):
        await bot.process_commands(message)


@bot.event
async def on_command_error(error, ctx):
    channel = ctx.message.channel
    if isinstance(error, commands.MissingRequiredArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.BadArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.DisabledCommand):
        await bot.send_message(channel, "That command is disabled.")
    elif isinstance(error, commands.CommandInvokeError):
        logger.exception("Exception in command '{}'".format(
            ctx.command.qualified_name), exc_info=error.original)
        oneliner = "Error in command '{}' - {}: {}".format(
            ctx.command.qualified_name, type(error.original).__name__,
            str(error.original))
        await ctx.bot.send_message(channel, inline(oneliner))
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, commands.NoPrivateMessage):
        await bot.send_message(channel, "That command is not "
                                        "available in DMs.")
    else:
        logger.exception(type(error).__name__, exc_info=error)


async def get_oauth_url():
    try:
        data = await bot.application_info()
    except Exception as e:
        return "Couldn't retrieve invite link.Error: {}".format(e)
    return discord.utils.oauth_url(data.id)


async def set_bot_owner():
    if settings.self_bot:
        settings.owner = bot.user.id
        return "[Selfbot mode]"

    if bot.settings.owner:
        owner = discord.utils.get(bot.get_all_members(),
                                  id=bot.settings.owner)
        if not owner:
            try:
                owner = await bot.get_user_info(bot.settings.owner)
            except:
                owner = None
            else:
                owner = bot.settings.owner # Just the ID then
        return owner

    how_to = "Do `[p]set owner` in chat to set it"

    if bot.user.bot: # Can fetch owner
        try:
            data = await bot.application_info()
            settings.owner = data.owner.id
            settings.save_settings()
            return data.owner
        except:
            return "Failed to fetch owner. " + how_to
    else:
        return "Yet to be set. " + how_to


def check_folders():
    folders = ("data", "data/red", "cogs", "cogs/utils")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def interactive_setup():
    first_run = settings.bot_settings == settings.default_settings

    if first_run:
        print("Red - First run configuration\n")
        print("If you haven't already, create a new account:\n"
              "https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/"
              "#creating-a-new-bot-account")
        print("and obtain your bot's token like described.")

    if not settings.login_credentials:
        print("\nInsert your bot's token:")
        while settings.token is None and settings.email is None:
            choice = input("> ")
            if "@" not in choice and len(choice) >= 50:  # Assuming token
                settings.token = choice
            elif "@" in choice:
                settings.email = choice
                settings.password = input("\nPassword> ")
            else:
                print("That doesn't look like a valid token.")
        settings.save_settings()

    if not settings.prefixes:
        print("\nChoose a prefix. A prefix is what you type before a command."
              "\nA typical prefix would be the exclamation mark.\n"
              "Can be multiple characters. You will be able to change it "
              "later and add more of them.\nChoose your prefix:")
        confirmation = False
        while confirmation is False:
            new_prefix = ensure_reply("\nPrefix> ").strip()
            print("\nAre you sure you want {0} as your prefix?\nYou "
                  "will be able to issue commands like this: {0}help"
                  "\nType yes to confirm or no to change it".format(
                      new_prefix))
            confirmation = get_answer()
        settings.prefixes = [new_prefix]
        settings.save_settings()

    if first_run:
        print("\nInput the admin role's name. Anyone with this role in Discord"
              " will be able to use the bot's admin commands")
        print("Leave blank for default name (Transistor)")
        settings.default_admin = input("\nAdmin role> ")
        if settings.default_admin == "":
            settings.default_admin = "Transistor"
        settings.save_settings()

        print("\nInput the moderator role's name. Anyone with this role in"
              " Discord will be able to use the bot's mod commands")
        print("Leave blank for default name (Process)")
        settings.default_mod = input("\nModerator role> ")
        if settings.default_mod == "":
            settings.default_mod = "Process"
        settings.save_settings()

        print("\nThe configuration is done. Leave this window always open to"
              " keep Red online.\nAll commands will have to be issued through"
              " Discord's chat, *this window will now be read only*.\n"
              "Please read this guide for a good overview on how Red works:\n"
              "https://twentysix26.github.io/Red-Docs/red_getting_started/\n"
              "Press enter to continue")
        input("\n")


def set_logger():
    global logger

    logger = logging.getLogger("red")
    logger.setLevel(logging.INFO)

    red_format = logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(red_format)
    if settings.debug:
        stdout_handler.setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    else:
        stdout_handler.setLevel(logging.INFO)
        logger.setLevel(logging.INFO)

    fhandler = logging.handlers.RotatingFileHandler(
        filename='data/red/red.log', encoding='utf-8', mode='a',
        maxBytes=10**7, backupCount=5)
    fhandler.setFormatter(red_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)

    dpy_logger = logging.getLogger("discord")
    if settings.debug:
        dpy_logger.setLevel(logging.DEBUG)
    else:
        dpy_logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(
        filename='data/red/discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    dpy_logger.addHandler(handler)


def ensure_reply(msg):
    choice = ""
    while choice == "":
        choice = input(msg)
    return choice


def get_answer():
    choices = ("yes", "y", "no", "n")
    c = ""
    while c not in choices:
        c = input(">").lower()
    if c.startswith("y"):
        return True
    else:
        return False


def set_cog(cog, value):
    data = dataIO.load_json("data/red/cogs.json")
    data[cog] = value
    dataIO.save_json("data/red/cogs.json", data)


def load_cogs():
    defaults = ("alias", "audio", "customcom", "downloader", "economy",
                "general", "image", "mod", "streams", "trivia")

    try:
        registry = dataIO.load_json("data/red/cogs.json")
    except:
        registry = {}

    bot.load_extension('cogs.owner')
    owner_cog = bot.get_cog('Owner')
    if owner_cog is None:
        print("The owner cog is missing. It contains core functions without "
              "which Red cannot function. Reinstall.")
        exit(1)

    if settings._no_cogs:
        logger.debug("Skipping initial cogs loading (--no-cogs)")
        if not os.path.isfile("data/red/cogs.json"):
            dataIO.save_json("data/red/cogs.json", {})
        return

    failed = []
    extensions = owner_cog._list_cogs()

    if not registry: # All default cogs enabled by default
        for ext in defaults:
            registry["cogs." + ext] = True

    for extension in extensions:
        if extension.lower() == "cogs.owner":
            continue
        to_load = registry.get(extension, False)
        if to_load:
            try:
                owner_cog._load_cog(extension)
            except Exception as e:
                print("{}: {}".format(e.__class__.__name__, str(e)))
                logger.exception(e)
                failed.append(extension)
                registry[extension] = False

    dataIO.save_json("data/red/cogs.json", registry)

    if failed:
        print("\nFailed to load: {}\n".format(" ".join(failed)))


def main():
    check_folders()
    if not settings.no_prompt:
        interactive_setup()
    load_cogs()

    print("Logging into Discord...")
    bot.uptime = datetime.datetime.now()

    if settings.login_credentials:
        yield from bot.login(*settings.login_credentials,
                             bot=not settings.self_bot)
    else:
        print("No credentials available to login.")
        raise RuntimeError()
    yield from bot.connect()

if __name__ == '__main__':
    sys.stdout = TextIOWrapper(sys.stdout.detach(),
                               encoding=sys.stdout.encoding,
                               errors="replace",
                               line_buffering=True)
    set_logger()
    error = False
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except discord.LoginFailure:
        error = True
        logger.error(traceback.format_exc())
        if not settings.no_prompt:
            choice = input("Invalid login credentials. "
                           "If they worked before Discord might be having temporary "
                           "technical issues.\nIn this case, press enter and "
                           "try again later.\nOtherwise you can type 'reset' to "
                           "reset the current credentials and set them "
                           "again the next start.\n> ")
            if choice.lower().strip() == "reset":
                settings.token = None
                settings.email = None
                settings.password = None
                settings.save_settings()
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())
    except:
        error = True
        logger.error(traceback.format_exc())
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
        if error:
            exit(1)
