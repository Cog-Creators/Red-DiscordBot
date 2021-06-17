import re
from redbot.core.commands import Converter, BadArgument
from redbot.core.i18n import Translator

_ = Translator("Mod", __file__)

_id_regex = re.compile(r"([0-9]{15,20})$")
_mention_regex = re.compile(r"<@!?([0-9]{15,20})>$")


class RawUserIds(Converter):
    async def convert(self, ctx, argument):
        # This is for the hackban and unban commands, where we receive IDs that
        # are most likely not in the guild.
        # Mentions are supported, but most likely won't ever be in cache.

        if match := _id_regex.match(argument) or _mention_regex.match(argument):
            return int(match.group(1))

        raise BadArgument(_("{} doesn't look like a valid user ID.").format(argument))
