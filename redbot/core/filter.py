import discord
import os
from typing import Union, Tuple, List
import re

from . import Config, errors
from .utils.common_filters import URL_RE, MASS_MENTION_RE, OTHER_MENTION_RE, INVITE_URL_RE

default_guild = {"filter": []}

default_channel = {"filter": []}


def _register_defaults():
    _conf.register_guild(**default_guild)
    _conf.register_channel(**default_channel)


if not os.environ.get("BUILDING_DOCS"):
    _conf = Config.get_conf(None, 384734293238749, cog_name="Filter", force_registration=True)
    _register_defaults()


async def add(text: str, destination: Union[discord.Guild, discord.TextChannel]):
    """
    Adds text to the filter

    Parameters
    ----------
    text: str
        The text to add to the filter
    destination: discord.Guild or discord.TextChannel
        The target of the filter to be added
    """
    if isinstance(destination, discord.Guild):
        async with _conf.guild(destination).filter() as guild_filter:
            if text.lower() in guild_filter:
                raise errors.FilterAlreadyExists(text=text, target=destination)
            else:
                guild_filter.append(text.lower())
    elif isinstance(destination, discord.TextChannel):
        async with _conf.channel(destination).filter() as channel_filter:
            if text.lower() in channel_filter:
                raise errors.FilterAlreadyExists(text=text, target=destination)
            else:
                channel_filter.append(text.lower())
    else:
        raise errors.InvalidTarget(target=destination)


async def remove(text: str, destination: Union[discord.Guild, discord.TextChannel]):
    """
    Removes text from the filter

    Parameters
    ----------
    text: str
        The text to remove from the filter
    destination: discord.Guild or discord.TextChannel
        The target of the filter to be removed
    """
    if isinstance(destination, discord.Guild):
        async with _conf.guild(destination).filter() as guild_filter:
            if text.lower() not in guild_filter:
                raise errors.NonExistentFilter(text=text, target=destination)
            else:
                guild_filter.remove(text.lower())
    elif isinstance(destination, discord.TextChannel):
        async with _conf.channel(destination).filter() as channel_filter:
            if text.lower() not in channel_filter:
                raise errors.NonExistentFilter(text=text, target=destination)
            else:
                channel_filter.remove(text.lower())
    else:
        raise errors.InvalidTarget(target=destination)


async def check(
    msg: discord.Message,
    check_urls: bool = False,
    check_invites: bool = False,
    check_mass_mentions: bool = False,
    check_other_mentions: int = 0,
) -> Tuple[bool, Union[str, List[re.Match], None]]:
    """
    Checks the message for filtered content.

    Parameters
    ----------
    msg: discord.Message
        The message to check
    check_urls: bool, optional
        Whether to check for urls in the message
    check_invites: bool, optional
        Whether to check for invites in the message
    check_mass_mentions: bool, optional:
        Whether to check for mass mentions (e.g. everyone or here) in the message
    check_other_mentions: int, optional:
        If greater than 0, the number of other mentions (e.g. user, role, channel) that 
        indicate the message should be filtered
    
    Returns
    -------
    Tuple[bool, Union[str, List[re.Match], None]]
        A tuple with the first value representing whether the message should be filtered
        and the second being the match or list of matches, or None if the message is not
        filtered
    """
    channel = msg.channel
    guild = msg.guild

    guild_filter = await _conf.guild(guild).filter()
    channel_filter = await _conf.channel(channel).filter()

    if check_urls:
        res = URL_RE.findall(msg.content)
        if res:
            return True, res
    if check_invites:
        res = INVITE_URL_RE.findall(msg.content)
        if res:
            return True, res
    if check_mass_mentions:
        res = MASS_MENTION_RE.findall(msg.content)
        if res:
            return True, res
    if check_other_mentions > 0:
        res = OTHER_MENTION_RE.findall(msg.content)
        if len(res) >= check_other_mentions:
            return True, res

    for term in guild_filter:
        if term in msg.content.lower():
            return True, term
    for term in channel_filter:
        if term in msg.content.lower():
            return True, term
    return False, None


async def check_name(member: discord.Member) -> bool:
    """
    Checks if the member's name or nick match anything in the filter

    Parameters
    ----------
    member: discord.Member
        The member to check
    
    Returns
    -------
    bool
        True if the user's nickname (or name, if the user doesn't have a nickname in the guild) 
        contains any filtered content, otherwise False
    """
    guild = member.guild
    guild_filter = await _conf.guild(guild).filter()

    for term in guild_filter:
        if member.nick and term in member.nick:
            return True
        elif not member.nick and term in member.name:
            return True
    return False
