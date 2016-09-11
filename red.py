from discord.ext import commands
import discord
from cogs.utils.settings import Settings
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import inline
import asyncio
import os
import time
import sys
import logging
import logging.handlers
import shutil
import traceback

#
#  Red, a Discord bot by Twentysix, based on discord.py and its command extension
#                   https://github.com/Twentysix26/
#
#
# red.py and cogs/utils/checks.py both contain some modified functions originally made by Rapptz
#             https://github.com/Rapptz/RoboDanny/tree/async
#

description = "Red - A multifunction Discord bot by Twentysix"

formatter = commands.HelpFormatter(show_check_failure=False)

bot = commands.Bot(command_prefix=["_"], formatter=formatter,
                   description=description, pm_help=None)

settings = Settings()


@bot.event
async def on_ready():
    owner_cog = bot.get_cog('Owner')
    total_cogs = len(owner_cog._list_cogs())
    users = len(set(bot.get_all_members()))
    servers = len(bot.servers)
    channels = len([c for c in bot.get_all_channels()])
    if not hasattr(bot, "uptime"):
        bot.uptime = int(time.perf_counter())
    if settings.login_type == "token" and settings.owner == "id_here":
        await set_bot_owner()
    print('------')
    print("{} is now online.".format(bot.user.name))
    print('------')
    print("Connected to:")
    print("{} servers".format(servers))
    print("{} channels".format(channels))
    print("{} users".format(users))
    print("\n{}/{} active cogs with {} commands".format(
        len(bot.cogs), total_cogs, len(bot.commands)))
    prefix_label = "Prefixes:" if len(bot.command_prefix) > 1 else "Prefix:"
    print("{} {}\n".format(prefix_label, " ".join(bot.command_prefix)))
    if settings.login_type == "token":
        print("------")
        print("Use this url to bring your bot to a server:")
        url = await get_oauth_url()
        bot.oauth_url = url
        print(url)
        print("------")
    await bot.get_cog('Owner').disable_commands()


@bot.event
async def on_command(command, ctx):
    pass


@bot.event
async def on_message(message):
    if user_allowed(message):
        await bot.process_commands(message)


@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.MissingRequiredArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.BadArgument):
        await send_cmd_help(ctx)
    elif isinstance(error, commands.DisabledCommand):
        await bot.send_message(ctx.message.channel,
            "That command is disabled.")
    elif isinstance(error, commands.CommandInvokeError):
        logger.exception("Exception in command '{}'".format(
            ctx.command.qualified_name), exc_info=error.original)
        oneliner = "Error in command '{}' - {}: {}".format(
            ctx.command.qualified_name, type(error.original).__name__,
            str(error.original))
        await ctx.bot.send_message(ctx.message.channel, inline(oneliner))
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        logger.exception(type(error).__name__, exc_info=error)

async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        pages = bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)
    else:
        pages = bot.formatter.format_help_for(ctx, ctx.command)
        for page in pages:
            await bot.send_message(ctx.message.channel, page)


def user_allowed(message):

    author = message.author

    mod = bot.get_cog('Mod')

    if mod is not None:
        if settings.owner == author.id:
            return True
        if not message.channel.is_private:
            server = message.server
            names = (settings.get_server_admin(
                server), settings.get_server_mod(server))
            results = map(
                lambda name: discord.utils.get(author.roles, name=name), names)
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


async def get_oauth_url():
    try:
        data = await bot.application_info()
    except AttributeError:
        return "Your discord.py is outdated. Couldn't retrieve invite link."
    return discord.utils.oauth_url(data.id)

async def set_bot_owner():
    try:
        data = await bot.application_info()
        settings.owner = data.owner.id
    except AttributeError:
        print("Your discord.py is outdated. Couldn't retrieve owner's ID.")
        return
    print("{} has been recognized and set as owner.".format(data.owner.name))


def check_folders():
    folders = ("data", "data/red", "cogs", "cogs/utils")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_configs():
    if settings.bot_settings == settings.default_settings:
        print("Red - First run configuration\n")
        print("If you haven't already, create a new account:\n"
              "https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/"
              "#creating-a-new-bot-account")
        print("and obtain your bot's token like described.")
        print("\nInsert your bot's token:")

        choice = input("> ")

        if "@" not in choice and len(choice) >= 50:  # Assuming token
            settings.login_type = "token"
            settings.email = choice
        elif "@" in choice:
            settings.login_type = "email"
            settings.email = choice
            settings.password = input("\nPassword> ")
        else:
            os.remove('data/red/settings.json')
            input("Invalid input. Restart Red and repeat the configuration "
                  "process.")
            exit(1)

        print("\nChoose a prefix. A prefix is what you type before a command.\n"
              "A typical prefix would be the exclamation mark.\n"
              "Can be multiple characters. You will be able to change it "
              "later and add more of them.\nChoose your prefix:")
        confirmation = False
        while confirmation is False:
            new_prefix = ensure_reply("\nPrefix> ").strip()
            print("\nAre you sure you want {0} as your prefix?\nYou "
                  "will be able to issue commands like this: {0}help"
                  "\nType yes to confirm or no to change it".format(new_prefix))
            confirmation = get_answer()

        settings.prefixes = [new_prefix]
        if settings.login_type == "email":
            print("\nOnce you're done with the configuration, you will have to type "
                  "'{}set owner' *in Discord's chat*\nto set yourself as owner.\n"
                  "Press enter to continue".format(new_prefix))
            settings.owner = input("") # Shh, they will never know it's here
            if settings.owner == "":
                settings.owner = "id_here"
            if not settings.owner.isdigit() or len(settings.owner) < 17:
                if settings.owner != "id_here":
                    print("\nERROR: What you entered is not a valid ID. Set "
                          "yourself as owner later with {}set owner".format(new_prefix))
                settings.owner = "id_here"
        else:
            settings.owner = "id_here"

        print("\nInput the admin role's name. Anyone with this role in Discord will be "
              "able to use the bot's admin commands")
        print("Leave blank for default name (Transistor)")
        settings.default_admin = input("\nAdmin role> ")
        if settings.default_admin == "":
            settings.default_admin = "Transistor"

        print("\nInput the moderator role's name. Anyone with this role in Discord will "
              "be able to use the bot's mod commands")
        print("Leave blank for default name (Process)")
        settings.default_mod = input("\nModerator role> ")
        if settings.default_mod == "":
            settings.default_mod = "Process"

        print("\nThe configuration is done. Leave this window always open to keep "
              "Red online.\nAll commands will have to be issued through Discord's "
              "chat, *this window will now be read only*.\nPress enter to continue")
        input("\n")

    if not os.path.isfile("data/red/cogs.json"):
        print("Creating new cogs.json...")
        dataIO.save_json("data/red/cogs.json", {})

def set_logger():
    global logger
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(
        filename='data/red/discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    logger.addHandler(handler)

    logger = logging.getLogger("red")
    logger.setLevel(logging.INFO)

    red_format = logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(red_format)
    stdout_handler.setLevel(logging.INFO)

    fhandler = logging.handlers.RotatingFileHandler(
        filename='data/red/red.log', encoding='utf-8', mode='a',
        maxBytes=10**7, backupCount=5)
    fhandler.setFormatter(red_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)

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
    try:
        if sys.argv[1] == "--no-prompt":
            no_prompt = True
        else:
            no_prompt = False
    except:
        no_prompt = False

    try:
        registry = dataIO.load_json("data/red/cogs.json")
    except:
        registry = {}

    bot.load_extension('cogs.owner')
    owner_cog = bot.get_cog('Owner')
    if owner_cog is None:
        print("You got rid of the damn OWNER cog, it has special functions"
              " that I require to run.\n\n"
              "I can't start without it!")
        print()
        print("Go here to find a new copy:\n{}".format(
            "https://github.com/Twentysix26/Red-DiscordBot"))
        exit(1)

    failed = []
    extensions = owner_cog._list_cogs()
    for extension in extensions:
        if extension.lower() == "cogs.owner":
            continue
        in_reg = extension in registry
        if in_reg is False:
            if no_prompt is True:
                registry[extension] = False
                continue
            print("\nNew extension: {}".format(extension))
            print("Load it?(y/n)")
            if not get_answer():
                registry[extension] = False
                continue
            registry[extension] = True
        if not registry[extension]:
            continue
        try:
            owner_cog._load_cog(extension)
        except Exception as e:
            print("{}: {}".format(e.__class__.__name__, str(e)))
            logger.exception(e)
            failed.append(extension)
            registry[extension] = False

    if extensions:
        dataIO.save_json("data/red/cogs.json", registry)

    if failed:
        print("\nFailed to load: ", end="")
        for m in failed:
            print(m + " ", end="")
        print("\n")

    return owner_cog


def main():
    global settings

    check_folders()
    check_configs()
    set_logger()
    owner_cog = load_cogs()
    if settings.prefixes != []:
        bot.command_prefix = settings.prefixes
    else:
        print("No prefix set. Defaulting to !")
        bot.command_prefix = ["!"]
        if settings.owner != "id_here":
            print("Use !set prefix to set it.")
        else:
            print("Once you're owner use !set prefix to set it.")
    if settings.owner == "id_here" and settings.login_type == "email":
        print("Owner has not been set yet. Do '{}set owner' in chat to set "
              "yourself as owner.".format(bot.command_prefix[0]))
    else:
        owner_cog.owner.hidden = True  # Hides the set owner command from help
    print("-- Logging in.. --")
    if os.name == "nt" and os.path.isfile("update.bat"):
        print("Make sure to keep your bot updated by running the file "
              "update.bat")
    else:
        print("Make sure to keep your bot updated by using: git pull")
        print("and: pip3 install -U git+https://github.com/Rapptz/"
              "discord.py@master#egg=discord.py[voice]")
    print("Official server: https://discord.me/Red-DiscordBot")
    if settings.login_type == "token":
        try:
            yield from bot.login(settings.email)
        except TypeError as e:
            print(e)
            msg = ("\nYou are using an outdated discord.py.\n"
                   "update your discord.py with by running this in your cmd "
                   "prompt/terminal.\npip3 install --upgrade git+https://"
                   "github.com/Rapptz/discord.py@async")
            sys.exit(msg)
    else:
        yield from bot.login(settings.email, settings.password)
    yield from bot.connect()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except discord.LoginFailure:
        logger.error(traceback.format_exc())
        choice = input("Invalid login credentials. "
            "If they worked before Discord might be having temporary "
            "technical issues.\nIn this case, press enter and "
            "try again later.\nOtherwise you can type 'reset' to "
            "delete the current configuration and redo the setup process "
            "again the next start.\n> ")
        if choice.strip() == "reset":
            shutil.copy('data/red/settings.json',
                        'data/red/settings-{}.bak'.format(int(time.time())))
            os.remove('data/red/settings.json')
    except:
        logger.error(traceback.format_exc())
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
