from discord.ext import commands
import discord
from cogs.utils import checks
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

lock = False

@bot.event
async def on_ready():
    users = str(len([m for m in bot.get_all_members()]))
    servers = str(len(bot.servers))
    channels = str(len([c for c in bot.get_all_channels()]))
    print('------')
    print(bot.user.name + " is now online.")
    print('------')
    print("Connected to:")
    print(servers + " servers")
    print(channels + " channels")
    print(users + " users")
    print("\n{0} active cogs with {1} commands\n".format(str(len(bot.cogs)), str(len(bot.commands))))
    bot.uptime = int(time.perf_counter())

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

    Example: load cogs.mod"""
    module = module.strip()
    if not module in list_cogs():
        await bot.say("That module doesn't exist.")
        return
    set_cog(module, True)
    try:
        bot.load_extension(module)
    except Exception as e:
        await bot.say('{}: {}'.format(type(e).__name__, e))
    else:
        await bot.say("Module enabled.")

@bot.command()
@checks.is_owner()
async def unload(*, module : str):
    """Unloads a module

    Example: unload cogs.mod"""
    module = module.strip()
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

    Example: reload cogs.mod"""
    module = module.strip()
    if not module in list_cogs():
        await bot.say("That module doesn't exist.")
        return
    set_cog(module, True)
    try:
        bot.unload_extension(module)
        bot.load_extension(module)
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
        censor = (settings["EMAIL"], settings["PASSWORD"])
        r = "[EXPUNGED]"
        for w in censor:
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
    data = load_settings()
    if data["OWNER"] != "id_here":
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
    bot.command_prefix = list(prefixes)
    data = load_settings()
    data["PREFIXES"] = list(prefixes)
    with open("data/red/settings.json", "w") as f:
            f.write(json.dumps(data))
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
    await bot.edit_profile(settings["PASSWORD"], username=" ".join(name))
    await bot.say("Done.")

@bot.command()
@checks.is_owner()
async def shutdown():
    """Shuts down Red"""
    await bot.logout()

@bot.command()
@checks.is_owner()
async def join(invite_url : discord.Invite):
    """Joins new server"""
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
        if checks.settings["OWNER"] == author.id:
            return True
        if not message.channel.is_private:
            if discord.utils.get(author.roles, name=checks.settings["ADMIN_ROLE"]) is not None:
                return True
            if discord.utils.get(author.roles, name=checks.settings["MOD_ROLE"]) is not None:
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
        data = load_settings()
        data["OWNER"] = author.id
        with open("data/red/settings.json", "w") as f:
            f.write(json.dumps(data))
        checks.owner = data["OWNER"]
        print(author.name + " has been set as owner. A restart is required.")
        lock = False
    else:
        print("setowner request has been ignored.")
        lock = False

def load_settings():
    try:
        with open('data/red/settings.json', "r") as f:
            return json.load(f)
    except:
        raise("Couldn't load credentials.")

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
    settings_path = "data/red/settings.json"
    settings = {"EMAIL" : "EmailHere", "PASSWORD" : "PasswordHere", "OWNER" : "id_here", "PREFIXES" : [], "ADMIN_ROLE" : "Transistor", "MOD_ROLE" : "Process"}
    if not os.path.isfile(settings_path):

        print("Red - First run configuration")
        print("If you don't have one, create a NEW ACCOUNT for Red. Do *not* use yours. (https://discordapp.com)")
        settings["EMAIL"] = input("\nEmail> ")
        settings["PASSWORD"] = input("\nPassword> ")

        if not settings["EMAIL"] or not settings["PASSWORD"]:
            raise("Email and password cannot be empty.")

        if "@" not in settings["EMAIL"]:
            raise("Your email is invalid.")
        
        print("\nChoose a prefix (or multiple ones, one at once) for the commands. Type exit when you're done. Example prefix: !")
        settings["PREFIXES"] = []
        new_prefix = ""
        while new_prefix.lower() != "exit" or settings["PREFIXES"] == []:
            new_prefix = input("Prefix> ")
            if new_prefix.lower() != "exit" and new_prefix != "":
                settings["PREFIXES"].append(new_prefix)

        print("\nInput *your own* ID. You can type \@Yourname in chat to see it (copy only the numbers).")
        print("If you want, you can also do it later with [prefix]set owner. Leave empty in that case.")
        settings["OWNER"] = input("\nID> ")
        if settings["OWNER"] == "": settings["OWNER"] = "id_here"

        print("\nInput the admin role's name. Anyone with this role will be able to use the bot's admin commands")
        print("Leave blank for default name (Transistor)")
        settings["ADMIN_ROLE"] = input("\nAdmin role> ")
        if settings["ADMIN_ROLE"] == "": settings["ADMIN_ROLE"] = "Transistor"

        print("\nInput the moderator role's name. Anyone with this role will be able to use the bot's mod commands")
        print("Leave blank for default name (Process)")
        settings["MOD_ROLE"] = input("\nAdmin role> ")
        if settings["MOD_ROLE"] == "": settings["MOD_ROLE"] = "Process"

        with open(settings_path, "w") as f:
            f.write(json.dumps(settings))

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
    handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
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
    check_folders()
    check_configs()
    set_logger()
    settings = load_settings()
    checks.owner = settings["OWNER"]
    load_cogs()
    bot.command_prefix = settings["PREFIXES"]
    yield from bot.login(settings["EMAIL"], settings["PASSWORD"])
    yield from bot.connect()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except discord.LoginFailure:
        print("Invalid login credentials. Restart Red and configure it properly.")
        os.remove('data/red/settings.json') # Hopefully this won't backfire in case of discord servers' problems
    except Exception as e:
        print(e)
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()
