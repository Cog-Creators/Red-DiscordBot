import re
from datetime import timedelta
from typing import TYPE_CHECKING

import discord

from . import BadArgument
from ..i18n import Translator

if TYPE_CHECKING:
    from .context import Context

__all__ = ["GuildConverter", "timedelta_converter"]

_ = Translator("commands.converter", __file__)

ID_REGEX = re.compile(r"([0-9]{15,21})")

# I could keep this one long string, but this is much easier to read/extend.
TIME_RE_STRING = r"\s?".join(
    [
        r"((?P<days>\d+?)\s?(d(ays?)?))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m))?",
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)

TIME_RE = re.compile(TIME_RE_STRING, re.I)


class GuildConverter(discord.Guild):
    """Converts to a `discord.Guild` object.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by name.
    """

    @classmethod
    async def convert(cls, ctx: "Context", argument: str) -> discord.Guild:
        match = ID_REGEX.fullmatch(argument)

        if match is None:
            ret = discord.utils.get(ctx.bot.guilds, name=argument)
        else:
            guild_id = int(match.group(1))
            ret = ctx.bot.get_guild(guild_id)

        if ret is None:
            raise BadArgument(_('Server "{name}" not found.').format(name=argument))

        return ret


def timedelta_converter(argument: str) -> timedelta:
    """
    Attempts to parse a user input string as a timedelta

    Arguments
    ---------
    argument: str
        String to attempt to treat as a timedelta

    Returns
    -------
    datetime.timedelta
        The parsed timedelta
    
    Raises
    ------
    ~discord.ext.commands.BadArgument
        No time was found from the given string.
    """
    matches = TIME_RE.match(argument)
    params = {k: int(v) for k, v in matches.groupdict().items() if v is not None}
    if not params:
        raise BadArgument("I couldn't turn that into a valid time period.")
    return timedelta(**params)
