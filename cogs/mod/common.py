import asyncio
from typing import List

import discord

from core import Config
from core.bot import Red

mute_unmute_issues = {
    "already_muted": "That user can't send messages in this channel.",
    "already_unmuted": "That user isn't muted in this channel!",
    "hierarchy_problem": "I cannot let you do that. You are not higher than "
                         "the user in the role hierarchy.",
    "permissions_issue": "Failed to mute user. I need the manage roles "
                         "permission and the user I'm muting must be "
                         "lower than myself in the role hierarchy."
}


async def mass_purge(messages: List[discord.Message],
                     channel: discord.TextChannel):
    while messages:
        if len(messages) > 1:
            await channel.delete_messages(messages[:100])
            messages = messages[100:]
        else:
            await messages[0].delete()
            messages = []
        await asyncio.sleep(1.5)


async def slow_deletion(messages: List[discord.Message]):
    for message in messages:
        try:
            await message.delete()
        except discord.HTTPException:
            pass


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
