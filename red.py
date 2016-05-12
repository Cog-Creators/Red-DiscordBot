from discord.ext import commands
import discord
from cogs.utils.settings import Settings
import json
import asyncio
import os
import time
import sys
import logging
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

description = """
Red - A multifunction Discord bot by Twentysix
"""

formatter = commands.HelpFormatter(show_check_failure=False)

bot = commands.Bot(command_prefix=["_"], formatter=formatter,
                   description=description, pm_help=None)

settings = Settings()

from cogs.utils import checks


@bot.event
async def on_ready():
    users = str(len(set(bot.get_all_members())))
    servers = str(len(bot.servers))
    channels = str(len([c for c in bot.get_all_channels()]))
    bot.uptime = int(time.perf_counter())
    print('------')
    print(bot.user.name + " is now online.")
    print('------')
    print("Connected to:")
    print(servers + " servers")
    print(channels + " channels")
    print(users + " users")
    print("\n{0} active cogs with {1} commands\n".format(
        str(len(bot.cogs)), str(len(bot.commands))))
    if settings.login_type == "token":
        print("------")
        print("Use this url to bring your bot to a server:")
        url = await get_oauth_url()
        bot.oauth_url = url
        print(url)
        print("------")


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
    endpoint = "https://discordapp.com/api/oauth2/applications/@me"
    if bot.headers.get('authorization') is None:
        bot.headers['authorization'] = "Bot {}".format(settings.email)

    async with bot.session.get(endpoint, headers=bot.headers) as resp:
        data = await resp.json()

    return discord.utils.oauth_url(data.get('id'))


def check_folders():
    folders = ("data", "data/red", "cogs", "cogs/utils")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_configs():
    if settings.bot_settings == settings.default_settings:
        print("Red - First run configuration\n")
        print("You either need a normal account or a bot account to use Red. "
              "*Do not* use your own.")
        print("For more information on bot accounts see: https://twentysix26."
              "github.io/Red-Docs/red_guide_bot_accounts/"
              "#creating-a-new-bot-account")
        print("If you decide to use a normal account, create an account for "
              "your bot on https://discordapp.com then enter your email here.")
        print("Otherwise make a bot account and copy the token from "
              "https://discordapp.com/developers/applications/me then enter "
              "your token here.")
        print("\nType your email or token:")

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

        print("\nChoose a prefix (or multiple ones, one at once) for the "
              "commands. Type exit when you're done. Example prefix: !")
        prefixes = []
        new_prefix = ""
        while new_prefix.lower() != "exit" or prefixes == []:
            new_prefix = input("Prefix> ")
            if new_prefix.lower() != "exit" and new_prefix != "":
                prefixes.append(new_prefix)
                # Remember we're using property's here, oh well...
        settings.prefixes = sorted(prefixes, reverse=True)

        print("\nIf you know what an User ID is, input *your own* now and"
              " press enter.")
        print("Otherwise you can just set yourself as owner later with "
              "'[prefix]set owner'. Leave empty and press enter in this case.")
        settings.owner = input("\nID> ")
        if settings.owner == "":
            settings.owner = "id_here"
        if not settings.owner.isdigit() or len(settings.owner) < 17:
            if settings.owner != "id_here":
                print("\nERROR: What you entered is not a valid ID. Set "
                      "yourself as owner later with [prefix]set owner")
            settings.owner = "id_here"

        print("\nInput the admin role's name. Anyone with this role will be "
              "able to use the bot's admin commands")
        print("Leave blank for default name (Transistor)")
        settings.default_admin = input("\nAdmin role> ")
        if settings.default_admin == "":
            settings.default_admin = "Transistor"

        print("\nInput the moderator role's name. Anyone with this role will "
              "be able to use the bot's mod commands")
        print("Leave blank for default name (Process)")
        settings.default_mod = input("\nModerator role> ")
        if settings.default_mod == "":
            settings.default_mod = "Process"

    cogs_s_path = "data/red/cogs.json"
    cogs = {}
    if not os.path.isfile(cogs_s_path):
        print("Creating new cogs.json...")
        with open(cogs_s_path, "w") as f:
            f.write(json.dumps(cogs))


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
    logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(
        filename='data/red/red.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]"))
    logger.addHandler(handler)


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
    with open('data/red/cogs.json', "r") as f:
        data = json.load(f)
    data[cog] = value
    with open('data/red/cogs.json', "w") as f:
        f.write(json.dumps(data))


def load_cogs():
    try:
        if sys.argv[1] == "--no-prompt":
            no_prompt = True
        else:
            no_prompt = False
    except:
        no_prompt = False

    try:
        with open('data/red/cogs.json', "r") as f:
            registry = json.load(f)
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
        if not (in_reg or no_prompt):
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
        with open('data/red/cogs.json', "w") as f:
            f.write(json.dumps(registry))

    if failed:
        print("\nFailed to load: ", end="")
        for m in failed:
            print(m + " ", end="")
        print("\n")

    return owner_cog


def main():
    global settings
    global checks

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
    if settings.owner == "id_here":
        print("Owner has not been set yet. Do '{}set owner' in chat to set "
              "yourself as owner.".format(bot.command_prefix[0]))
    else:
        owner_cog.owner.hidden = True  # Hides the set owner command from help
    print("-- Logging in.. --")
    print("Make sure to keep your bot updated by using: git pull")
    print("and: pip3 install --upgrade git+https://github.com/Rapptz/"
          "discord.py@async")
    if settings.login_type == "token":
        owner_cog._token.hidden = True
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
        print("Invalid login credentials. Restart Red and configure it"
              " properly.")
        shutil.copy('data/red/settings.json',
                    'data/red/settings-{}.bak'.format(int(time.time())))
        # Hopefully this won't backfire in case of discord servers' problems
        os.remove('data/red/settings.json')
    except:
        logger.error(traceback.format_exc())
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
