import asyncio
from datetime import timedelta
from typing import List, Iterable, Union

import discord

from redbot.core import Config
from redbot.core.bot import Red


async def mass_purge(messages: List[discord.Message], channel: discord.TextChannel):
    """Bulk delete messages from a channel.

    If more than 100 messages are supplied, the bot will delete 100 messages at
    a time, sleeping between each action.

    Note
    ----
    Messages must not be older than 14 days, and the bot must not be a user
    account.

    Parameters
    ----------
    messages : `list` of `discord.Message`
        The messages to bulk delete.
    channel : discord.TextChannel
        The channel to delete messages from.

    Raises
    ------
    discord.Forbidden
        You do not have proper permissions to delete the messages or you’re not
        using a bot account.
    discord.HTTPException
        Deleting the messages failed.

    """
    while messages:
        if len(messages) > 1:
            await channel.delete_messages(messages[:100])
            messages = messages[100:]
        else:
            await messages[0].delete()
            messages = []
        await asyncio.sleep(1.5)


async def slow_deletion(messages: Iterable[discord.Message]):
    """Delete a list of messages one at a time.

    Any exceptions raised when trying to delete the message will be silenced.

    Parameters
    ----------
    messages : `iterable` of `discord.Message`
        The messages to delete.

    """
    for message in messages:
        try:
            await message.delete()
        except discord.HTTPException:
            pass


def get_audit_reason(author: discord.Member, reason: str = None):
    """Construct a reason to appear in the audit log.

    Parameters
    ----------
    author : discord.Member
        The author behind the audit log action.
    reason : str
        The reason behind the audit log action.

    Returns
    -------
    str
        The formatted audit log reason.

    """
    return (
        "Action requested by {} (ID {}). Reason: {}".format(author, author.id, reason)
        if reason
        else "Action requested by {} (ID {}).".format(author, author.id)
    )


async def is_allowed_by_hierarchy(
    bot: Red, settings: Config, guild: discord.Guild, mod: discord.Member, user: discord.Member
):
    if not await settings.guild(guild).respect_hierarchy():
        return True
    is_special = mod == guild.owner or await bot.is_owner(mod)
    return mod.top_role.position > user.top_role.position or is_special


async def is_mod_or_superior(bot: Red, obj: Union[discord.Message, discord.Member, discord.Role]):
    """Check if an object has mod or superior permissions.

    If a message is passed, its author's permissions are checked. If a role is
    passed, it simply checks if it is one of either the admin or mod roles.

    Parameters
    ----------
    bot : redbot.core.bot.Red
        The bot object.
    obj : `discord.Message` or `discord.Member` or `discord.Role`
        The object to check permissions for.

    Returns
    -------
    bool
        :code:`True` if the object has mod permissions.

    Raises
    ------
    TypeError
        If the wrong type of ``obj`` was passed.

    """
    user = None
    if isinstance(obj, discord.Message):
        user = obj.author
    elif isinstance(obj, discord.Member):
        user = obj
    elif isinstance(obj, discord.Role):
        pass
    else:
        raise TypeError("Only messages, members or roles may be passed")

    server = obj.guild
    admin_role_id = await bot.db.guild(server).admin_role()
    mod_role_id = await bot.db.guild(server).mod_role()

    if isinstance(obj, discord.Role):
        return obj.id in [admin_role_id, mod_role_id]

    if await bot.is_owner(user):
        return True
    elif discord.utils.find(lambda r: r.id in (admin_role_id, mod_role_id), user.roles):
        return True
    else:
        return False


def strfdelta(delta: timedelta):
    """Format a timedelta object to a message with time units.

    Parameters
    ----------
    delta : datetime.timedelta
        The duration to parse.

    Returns
    -------
    str
        A message representing the timedelta with units.

    """
    s = []
    if delta.days:
        ds = "%i day" % delta.days
        if delta.days > 1:
            ds += "s"
        s.append(ds)
    hrs, rem = divmod(delta.seconds, 60 * 60)
    if hrs:
        hs = "%i hr" % hrs
        if hrs > 1:
            hs += "s"
        s.append(hs)
    mins, secs = divmod(rem, 60)
    if mins:
        s.append("%i min" % mins)
    if secs:
        s.append("%i sec" % secs)
    return " ".join(s)


async def is_admin_or_superior(
    bot: Red, obj: Union[discord.Message, discord.Member, discord.Role]
):
    """Same as `is_mod_or_superior` except for admin permissions.

    If a message is passed, its author's permissions are checked. If a role is
    passed, it simply checks if it is the admin role.

    Parameters
    ----------
    bot : redbot.core.bot.Red
        The bot object.
    obj : `discord.Message` or `discord.Member` or `discord.Role`
        The object to check permissions for.

    Returns
    -------
    bool
        :code:`True` if the object has admin permissions.

    Raises
    ------
    TypeError
        If the wrong type of ``obj`` was passed.

    """
    user = None
    if isinstance(obj, discord.Message):
        user = obj.author
    elif isinstance(obj, discord.Member):
        user = obj
    elif isinstance(obj, discord.Role):
        pass
    else:
        raise TypeError("Only messages, members or roles may be passed")

    admin_role_id = await bot.db.guild(obj.guild).admin_role()

    if isinstance(obj, discord.Role):
        return obj.id == admin_role_id

    if user and await bot.is_owner(user):
        return True
    elif discord.utils.get(user.roles, id=admin_role_id)
        return True
    else:
        return False
