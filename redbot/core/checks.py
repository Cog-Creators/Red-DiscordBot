import discord
from .commands import Requires, PrivilegeLevel, check as check_decorator


def owner():
    return Requires.get_decorator(PrivilegeLevel.BOT_OWNER, {})


# Alias for backwards compatibility
is_owner = owner


def guildowner_or_permissions(**perms):
    return Requires.get_decorator(PrivilegeLevel.GUILD_OWNER, perms)


def guildowner():
    return guildowner_or_permissions()


def admin_or_permissions(**perms):
    return Requires.get_decorator(PrivilegeLevel.ADMIN, perms)


def admin():
    return admin_or_permissions()


def mod_or_permissions(**perms):
    return Requires.get_decorator(PrivilegeLevel.MOD, perms)


def mod():
    return mod_or_permissions()


def bot_in_a_guild():
    async def predicate(ctx):
        return len(ctx.bot.guilds) > 0

    return check_decorator(predicate)


async def check_permissions(ctx, perms):
    if await ctx.bot.is_owner(ctx.author):
        return True
    elif not perms:
        return False
    resolved = ctx.channel.permissions_for(ctx.author)

    return resolved.administrator or all(
        getattr(resolved, name, None) == value for name, value in perms.items()
    )
