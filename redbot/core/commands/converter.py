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

class APIToken(discord.ext.commands.Converter):
    """Converts to a `dict` object.

    This will parse the input argument separating the key value pairs into a 
    format to be used for the core bots API token storage.
    
    This will split the argument by eiher `;` or `,` and return a dict
    to be stored. Since all API's are different and have different naming convention,
    this leaves the owness on the cog creator to clearly define how to setup the correct
    credential names for their cogs.
    """
    async def convert(self, ctx, argument) -> dict:
        bot = ctx.bot
        result = {}
        match = re.split(r";|,", argument)
        # provide two options to split incase for whatever reason one is part of the api key we're using
        if len(match) > 1:
            result[match[0]] = "".join(r for r in match[1:])
        else:
            raise BadArgument(_("The provided tokens are not in a valid format."))
        if not result:
            raise BadArgument(_("The provided tokens are not in a valid format."))
        return result
