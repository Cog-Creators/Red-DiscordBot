from datetime import datetime

import discord

from redbot.core import Config
from redbot.core.bot import Red


def get_min_time():
    now = datetime.utcnow().timestamp()
    twoweeks = 14 * 86400
    return datetime.fromtimestamp(now - twoweeks)


async def check_purge(ctx, messages):
    """Checks messages in the list, removing any
    that don't pass the check or that are too old,
    then deletes the remaining messages"""
    # Sort from newest to oldest
    to_delete = sorted(messages, key=lambda m: m.created_at, reverse=True)
    if ctx.bot.user.bot:
        while to_delete:
            await ctx.channel.delete_messages(to_delete[:100])
            to_delete = to_delete[100:]
    else:  # Not a bot, so cannot bulk delete
        for message in to_delete:
            await message.delete()


def get_audit_reason(author: discord.Member, reason: str = None):
    """Helper function to construct a reason to be provided
    as the reason to appear in the audit log."""
    return \
        "Action requested by {} (ID {}). Reason: {}".format(author, author.id, reason) if reason else \
        "Action requested by {} (ID {}).".format(author, author.id)


async def is_allowed_by_hierarchy(
        bot: Red, settings: Config, server: discord.Guild,
        mod: discord.Member, user: discord.Member):
    if not await settings.guild(server).respect_hierarchy():
        return True
    is_special = mod == server.owner or await bot.is_owner(mod)
    return mod.top_role.position > user.top_role.position or is_special


async def is_mod_or_superior(bot: Red, obj: discord.Message or discord.Member or discord.Role):
    user = None
    if isinstance(obj, discord.Message):
        user = obj.author
    elif isinstance(obj, discord.Member):
        user = obj
    elif isinstance(obj, discord.Role):
        pass
    else:
        raise TypeError('Only messages, members or roles may be passed')

    server = obj.guild
    admin_role_id = await bot.db.guild(server).admin_role()
    mod_role_id = await bot.db.guild(server).mod_role()

    if isinstance(obj, discord.Role):
        return obj.id in [admin_role_id, mod_role_id]
    mod_roles = [r for r in server.roles if r.id == mod_role_id]
    mod_role = mod_roles[0] if len(mod_roles) > 0 else None
    admin_roles = [r for r in server.roles if r.id == admin_role_id]
    admin_role = admin_roles[0] if len(admin_roles) > 0 else None

    if user and user == await bot.is_owner(user):
        return True
    elif admin_role and discord.utils.get(user.roles, name=admin_role):
        return True
    elif mod_role and discord.utils.get(user.roles, name=mod_role):
        return True
    else:
        return False


def strfdelta(delta):
    s = []
    if delta.days:
        ds = '%i day' % delta.days
        if delta.days > 1:
            ds += 's'
        s.append(ds)
    hrs, rem = divmod(delta.seconds, 60*60)
    if hrs:
        hs = '%i hr' % hrs
        if hrs > 1:
            hs += 's'
        s.append(hs)
    mins, secs = divmod(rem, 60)
    if mins:
        s.append('%i min' % mins)
    if secs:
        s.append('%i sec' % secs)
    return ' '.join(s)


async def is_admin_or_superior(bot: Red, obj: discord.Message or discord.Role or discord.Member):
    user = None
    if isinstance(obj, discord.Message):
        user = obj.author
    elif isinstance(obj, discord.Member):
        user = obj
    elif isinstance(obj, discord.Role):
        pass
    else:
        raise TypeError('Only messages, members or roles may be passed')

    server = obj.guild
    admin_role_id = await bot.db.guild(server).admin_role()

    if isinstance(obj, discord.Role):
        return obj.id == admin_role_id
    admin_roles = [r for r in server.roles if r.id == admin_role_id]
    admin_role = admin_roles[0] if len(admin_roles) > 0 else None

    if user and await bot.is_owner(user):
        return True
    elif admin_roles and discord.utils.get(user.roles, name=admin_role):
        return True
    else:
        return False
