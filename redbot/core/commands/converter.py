import re
from typing import TYPE_CHECKING

import discord

from . import BadArgument
from ..i18n import Translator

if TYPE_CHECKING:
    from .context import Context

__all__ = ["GuildConverter"]

_ = Translator("commands.converter", __file__)

ID_REGEX = re.compile(r"([0-9]{15,21})")


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
