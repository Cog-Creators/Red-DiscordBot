from discord.ext import commands
import discord.utils
import os.path
import json

#
# This is a modified version of checks.py, originally made by Rapptz
#
#                 https://github.com/Rapptz
#          https://github.com/Rapptz/RoboDanny/tree/async
#

try:
    with open("data/red/settings.json", "r") as f:
        settings = json.loads(f.read())
except Exception as e:
    print(e)
    settings = {"OWNER" : False, "default":{"ADMIN_ROLE" : False, "MOD_ROLE" : False}}

def is_owner_check(ctx):
    return ctx.message.author.id == settings["OWNER"]

def is_owner():
    return commands.check(is_owner_check)

# The permission system of the bot is based on a "just works" basis
# You have permissions and the bot has permissions. If you meet the permissions
# required to execute the command (and the bot does as well) then it goes through
# and you can execute the command.
# If these checks fail, then there are two fallbacks.
# A role with the name of Bot Mod and a role with the name of Bot Admin.
# Having these roles provides you access to certain commands without actually having
# the permissions required for them.
# Of course, the owner will always be able to execute commands.

def save_bot_settings(bot_settings=settings):
    with open("data/red/settings.json", "w") as f:
        f.write(json.dumps(bot_settings,sort_keys=True,indent=4,separators=(',',':')))

def update_old_settings():
    mod = settings["MOD_ROLE"]
    admin = settings["ADMIN_ROLE"]
    del settings["MOD_ROLE"]
    del settings["ADMIN_ROLE"]
    settings["default"] = {"MOD_ROLE":mod,"ADMIN_ROLE":admin}

def check_permissions(ctx, perms):
    if is_owner_check(ctx):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    resolved = ch.permissions_for(author)
    return all(getattr(resolved, name, None) == value for name, value in perms.items())

def role_or_permissions(ctx, check, **perms):
    if check_permissions(ctx, perms):
        return True

    ch = ctx.message.channel
    author = ctx.message.author
    if ch.is_private:
        return False # can't have roles in PMs

    role = discord.utils.find(check, author.roles)
    return role is not None

def mod_or_permissions(**perms):
    def predicate(ctx):
        if "default" not in settings:
            update_old_settings()
        if admin_or_permissions(**perms):
            return True
        sid = ctx.message.server.id
        if sid not in settings:
            mod_role = settings["default"]["MOD_ROLE"].lower()
            admin_role = settings["default"]["ADMIN_ROLE"].lower()
        else:
            mod_role = settings[sid]["MOD_ROLE"].lower()
            admin_role = settings[sid]["ADMIN_ROLE"].lower()
        return role_or_permissions(ctx, lambda r: r.name.lower() in (mod_role,admin_role), **perms)

    return commands.check(predicate)

def admin_or_permissions(**perms):
    def predicate(ctx):
        if "default" not in settings:
            update_old_settings()
        sid = ctx.message.server.id
        if sid not in settings:
            admin_role = settings["default"]["ADMIN_ROLE"]
        else:
            admin_role = settings[sid]["ADMIN_ROLE"]
        return role_or_permissions(ctx, lambda r: r.name.lower() == admin_role.lower(), **perms)

    return commands.check(predicate)
