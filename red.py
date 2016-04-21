from discord.ext import commands
import discord
from cogs.utils.settings import Settings
from random import choice as rndchoice
import threading
import datetime, re
import json, asyncio
import copy
import glob
import os
import time
import sys
import logging
import aiohttp
import importlib
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

lock = False

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
    print("\n{0} active cogs with {1} commands\n".format(str(len(bot.cogs)), str(len(bot.commands))))

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

@bot.command()
@checks.is_owner()
async def load(*, module : str):
    """Loads a module

    Example: load mod"""
    module = module.strip()
    if "cogs." not in module: module = "cogs." + module
    if not module in list_cogs():
        await bot.say("That module doesn't exist.")
        return
    set_cog(module, True)
    try:
        mod_obj = importlib.import_module(module)
        importlib.reload(mod_obj)
        bot.load_extension(mod_obj.__name__)
    except Exception as e:
        await bot.say('{}: {}'.format(type(e).__name__, e))
    else:
        await bot.say("Module enabled.")

@bot.command()
@checks.is_owner()
async def unload(*, module : str):
    """Unloads a module

    Example: unload mod"""
    module = module.strip()
    if "cogs." not in module: module = "cogs." + module
    if not module in list_cogs():
        await bot.say("That module doesn't exist.")
        return
    set_cog(module, False)
    try:
        bot.unload_extension(module)
    except Exception as e:
        await bot.say('{}: {}'.format(type(e).__name__, e))
    else:
        await bot.say("Module disabled.")

@bot.command(name="reload")
@checks.is_owner()
async def _reload(*, module : str):
    """Reloads a module

    Example: reload mod"""
    module = module.strip()
    if "cogs." not in module: module = "cogs." + module
    if not module in list_cogs():
        await bot.say("That module doesn't exist.")
        return
    set_cog(module, True)
    try:
        bot.unload_extension(module)
        mod_obj = importlib.import_module(module)
        importlib.reload(mod_obj)
        bot.load_extension(mod_obj.__name__)
    except Exception as e:
        await bot.say('\U0001f52b')
        await bot.say('{}: {}'.format(type(e).__name__, e))
    else:
        await bot.say("Module reloaded.")


@bot.command(pass_context=True, hidden=True) # Modified function, originally made by Rapptz
@checks.is_owner()
async def debug(ctx, *, code : str):
    """Evaluates code"""
    code = code.strip('` ')
    python = '```py\n{}\n```'
    result = None

    try:
        result = eval(code)
    except Exception as e:
        await bot.say(python.format(type(e).__name__ + ': ' + str(e)))
        return

    if asyncio.iscoroutine(result):
        result = await result

    result = python.format(result)
    if not ctx.message.channel.is_private:
        censor = (settings.email, settings.password)
        r = "[EXPUNGED]"
        for w in censor:
            if w != "":
                result = result.replace(w, r)
                result = result.replace(w.lower(), r)
                result = result.replace(w.upper(), r)
    await bot.say(result)

@bot.group(name="set", pass_context=True)
async def _set(ctx):
    """Changes settings"""
    if ctx.invoked_subcommand is None:
        await send_cmd_help(ctx)

@_set.command(pass_context=True)
async def owner(ctx):
    """Sets owner"""
    global lock
    msg = ctx.message
    if settings.owner != "id_here":
        await bot.say("Owner ID has already been set.")
        return
    if lock:
        await bot.say("A setowner request is already pending. Check the console.")
        return
    await bot.say("Confirm in the console that you're the owner.")
    lock = True
    t = threading.Thread(target=wait_for_answer, args=(ctx.message.author,))
    t.start()

@_set.command()
@checks.is_owner()
async def prefix(*prefixes):
    """Sets prefixes

    Must be separated by a space. Enclose in double
    quotes if a prefix contains spaces."""
    if prefixes == ():
        await bot.say("Example: setprefix [ ! ^ .")
        return
    bot.command_prefix = sorted(prefixes, reverse=True)
    settings.prefixes = sorted(prefixes, reverse=True)
    if len(prefixes) > 1:
        await bot.say("Prefixes set")
    else:
        await bot.say("Prefix set")

@_set.command(pass_context=True)
@checks.is_owner()
async def name(ctx, *name : str):
    """Sets Red's name"""
    if name == ():
        await send_cmd_help(ctx)
    await bot.edit_profile(settings.password, username=" ".join(name))
    await bot.say("Done.")

@_set.command(pass_context=True)
@checks.is_owner()
async def status(ctx, *status : str):
    """Sets Red's status"""
    if status != ():
        await bot.change_status(discord.Game(name=" ".join(status)))
    else:
        await bot.change_status(None)
    await bot.say("Done.")

@_set.command()
@checks.is_owner()
async def avatar(url : str):
    """Sets Red's avatar"""
    try:
        async with aiohttp.get(url) as r:
            data = await r.read()
        await bot.edit_profile(settings.password, avatar=data)
        await bot.say("Done.")
    except:
        await bot.say("Error.")

@_set.command(name="token")
@checks.is_owner()
async def _token(token : str):
    """Sets Red's login token"""
    if len(token) < 50:
        await bot.say("Invalid token.")
    else:
        settings.login_type = "token"
        settings.email = token
        settings.password = ""
        await bot.say("Token set. Restart me.")

@bot.command()
@checks.is_owner()
async def shutdown():
    """Shuts down Red"""
    await bot.logout()

@bot.command()
@checks.is_owner()
async def join(invite_url : discord.Invite):
    """Joins new server"""
    if bot.user.bot == True:
        msg = "I have a **BOT** tag, so I must be invited with an OAuth2 link:\n"
        msg += "`https://discordapp.com/oauth2/authorize?&client_id=`__**`MY_CLIENT_ID_HERE`**__`&scope=bot`\n"
        msg += "For more information: https://twentysix26.github.io/Red-Docs/red_guide_bot_accounts/#bot-invites"
        await bot.say(msg)
    else:
        try:
            await bot.accept_invite(invite_url)
            await bot.say("Server joined.")
        except discord.NotFound:
            await bot.say("The invite was invalid or expired.")
        except discord.HTTPException:
            await bot.say("I wasn't able to accept the invite. Try again.")

@bot.command(pass_context=True)
@checks.is_owner()
async def leave(ctx):
    """Leaves server"""
    message = ctx.message
    await bot.say("Are you sure you want me to leave this server? Type yes to confirm")
    response = await bot.wait_for_message(author=message.author)
    if response.content.lower().strip() == "yes":
        await bot.say("Alright. Bye :wave:")
        await bot.leave_server(message.server)
    else:
        await bot.say("Ok I'll stay here then.")

@bot.command(name="uptime")
async def _uptime():
    """Shows Red's uptime"""
    up = abs(bot.uptime - int(time.perf_counter()))
    up = str(datetime.timedelta(seconds=up))
    await bot.say("`Uptime: {}`".format(up))

def user_allowed(message):

    author = message.author

    mod = bot.get_cog('Mod')

    if mod is not None:
        if settings.owner == author.id:
            return True
        if not message.channel.is_private:
            server = message.server
            names = (settings.get_server_admin(server),settings.get_server_mod(server))
            results = map(lambda name: discord.utils.get(author.roles,name=name),names)
            for r in results:
                if r != None:
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

def wait_for_answer(author):
    global lock
    print(author.name + " requested to be set as owner. If this is you, type 'yes'. Otherwise press enter.")
    print("*DO NOT* set anyone else as owner.")
    choice = "None"
    while choice.lower() != "yes" and choice == "None":
        choice = input("> ")
    if choice == "yes":
        settings.owner = author.id
        print(author.name + " has been set as owner.")
        lock = False
        owner.hidden = True
    else:
        print("setowner request has been ignored.")
        lock = False

def list_cogs():
    cogs = glob.glob("cogs/*.py")
    clean = []
    for c in cogs:
        c = c.replace("/", "\\") # Linux fix
        clean.append("cogs." + c.split("\\")[1].replace(".py", ""))
    return clean

def check_folders():
    folders = ("data", "data/red", "cogs", "cogs/utils")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def check_configs():
    if settings.bot_settings == settings.default_settings:
        print("Red - First run configuration\n")
        print("You either need a normal account or a bot account to use Red. *Do not* use your own.")
        print("For more information on bot accounts see: https://discordapp.com/developers/docs/topics/oauth2#bot-vs-user-accounts")
        print("If you're not interested in a bot account, create a normal account on https://discordapp.com")
        print("Otherwise make one and copy the token from https://discordapp.com/developers/applications/me")
        print("\nType your email or token:")
        
        choice = input("> ")

        if "@" not in choice and len(choice) >= 50: #Assuming token
            settings.login_type = "token"
            settings.email = choice
        elif "@" in choice:
            settings.login_type = "email"
            settings.email = choice
            settings.password = input("\nPassword> ")
        else:
            os.remove('data/red/settings.json')
            input("Invalid input. Restart Red and repeat the configuration process.")
            exit(1)

        print("\nChoose a prefix (or multiple ones, one at once) for the commands. Type exit when you're done. Example prefix: !")
        prefixes = []
        new_prefix = ""
        while new_prefix.lower() != "exit" or prefixes == []:
            new_prefix = input("Prefix> ")
            if new_prefix.lower() != "exit" and new_prefix != "":
                prefixes.append(new_prefix)
                # Remember we're using property's here, oh well...
        settings.prefixes = sorted(prefixes, reverse=True)

        print("\nIf you know what an User ID is, input *your own* now and press enter.")
        print("Otherwise you can just set yourself as owner later with '[prefix]set owner'. Leave empty and press enter in this case.")
        settings.owner = input("\nID> ")
        if settings.owner == "": settings.owner = "id_here"
        if not settings.owner.isdigit() or len(settings.owner) < 17:
            if settings.owner != "id_here":
                print("\nERROR: What you entered is not a valid ID. Set yourself as owner later with [prefix]set owner")
            settings.owner = "id_here"

        print("\nInput the admin role's name. Anyone with this role will be able to use the bot's admin commands")
        print("Leave blank for default name (Transistor)")
        settings.default_admin = input("\nAdmin role> ")
        if settings.default_admin == "": settings.default_admin = "Transistor"

        print("\nInput the moderator role's name. Anyone with this role will be able to use the bot's mod commands")
        print("Leave blank for default name (Process)")
        settings.default_mod = input("\nModerator role> ")
        if settings.default_mod == "": settings.default_mod = "Process"

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
    handler = logging.FileHandler(filename='data/red/discord.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s %(module)s %(lineno)d %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
    logger.addHandler(handler)

    logger = logging.getLogger("red")
    logger.setLevel(logging.WARNING)
    handler = logging.FileHandler(filename='data/red/red.log', encoding='utf-8', mode='a')
    handler.setFormatter(logging.Formatter('%(asctime)s %(module)s %(lineno)d %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
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

    with open('data/red/cogs.json', "r") as f:
        data = json.load(f)
    register = tuple(data.keys()) #known cogs
    extensions = list_cogs()

    if extensions: print("\nLoading cogs...\n")

    failed = []
    for extension in extensions:
        if extension in register:
            if data[extension]:
                try:
                    bot.load_extension(extension)
                except Exception as e:
                    print(e)
                    failed.append(extension)
        else:
            if not no_prompt:
                print("\nNew extension: " + extension)
                print("Load it?(y/n)")
                if get_answer():
                    data[extension] = True
                    try:
                        bot.load_extension(extension)
                    except Exception as e:
                        print(e)
                        failed.append(extension)
                else:
                    data[extension] = False

    if extensions:
        with open('data/red/cogs.json', "w") as f:
            f.write(json.dumps(data))

    if failed:
        print("\nFailed to load: ", end="")
        for m in failed:
            print(m + " ", end="")
        print("\n")

def main():
    global settings
    global checks

    check_folders()
    check_configs()
    set_logger()
    load_cogs()
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
        print("Owner has not been set yet. Do '{}set owner' in chat to set yourself as owner.".format(bot.command_prefix[0]))
    else:
        owner.hidden = True  # Hides the set owner command from help
    print("-- Logging in.. --")
    print("Make sure to keep your bot updated by using: git pull")
    print("and: pip3 install --upgrade git+https://github.com/Rapptz/discord.py@async")
    if settings.login_type == "token":
        _token.hidden = True
        try:
            yield from bot.login(settings.email)
        except TypeError as e:
            print(e)
            msg = "\n"
            msg += "You are using an outdated discord.py.\n"
            msg += "update your discord.py with by running this in your cmd prompt/terminal.\n"
            msg += "pip3 install --upgrade git+https://github.com/Rapptz/discord.py@async"
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
        print("Invalid login credentials. Restart Red and configure it properly.")
        shutil.copy('data/red/settings.json', 'data/red/settings-{}.bak'.format(int(time.time())))
        os.remove('data/red/settings.json')  # Hopefully this won't backfire in case of discord servers' problems
    except:
        logger.error(traceback.format_exc())
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
