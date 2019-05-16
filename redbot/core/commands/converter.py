import re
import functools
from typing import TYPE_CHECKING, Optional, List, Dict

import discord
from discord.ext import commands as dpy_commands

from . import BadArgument
from ..i18n import Translator

if TYPE_CHECKING:
    from .context import Context

__all__ = ["GuildConverter", "APIToken", "DictConverter", "get_validated_dict_converter"]

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
    
    This will split the argument by either `;` ` `, or `,` and return a dict
    to be stored. Since all API's are different and have different naming convention,
    this leaves the onus on the cog creator to clearly define how to setup the correct
    credential names for their cogs.

    Note: Core usage of this has been replaced with DictConverter use instead.

    This may be removed at a later date (with warning)
    """

    async def convert(self, ctx, argument) -> dict:
        bot = ctx.bot
        result = {}
        match = re.split(r";|,| ", argument)
        # provide two options to split incase for whatever reason one is part of the api key we're using
        if len(match) > 1:
            result[match[0]] = "".join(r for r in match[1:])
        else:
            raise BadArgument(_("The provided tokens are not in a valid format."))
        if not result:
            raise BadArgument(_("The provided tokens are not in a valid format."))
        return result


class DictConverter(dpy_commands.Converter):
    """
    Converts pairs of space seperated values to a dict
    """

    def __init__(self, *expected_keys: str, split_commas=False):
        self.expected_keys = expected_keys
        self.split_commas = split_commas

    async def convert(self, ctx: "Context", argument: str) -> Dict[str, str]:

        ret: Dict[str, str] = {}
        pattern = r";|,| " if self.split_commas else " "
        args = re.split(pattern, argument)

        if len(args) % 2 != 0:
            raise BadArgument()

        iterator = iter(args)

        for key in iterator:
            if self.expected_keys and key not in self.expected_keys:
                raise BadArgument(_("Unexpected key {key}").format(key))

            ret[key] = next(iterator)

        return ret


def get_validated_dict_converter(*expected_keys: str, split_commas=False) -> type:
    """
    Returns a typechecking safe `DictConverter` suitable for use with discord.py
    """

    class PartialMeta(type(DictConverter)):
        __call__ = functools.partialmethod(
            type(DictConverter).__call__, *expected_keys, split_commas=split_commas
        )

    class ValidatedConverter(DictConverter, metaclass=PartialMeta):
        pass

    return ValidatedConverter
