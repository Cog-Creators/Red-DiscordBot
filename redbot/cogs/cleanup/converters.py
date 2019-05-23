from redbot.core.commands import Converter, BadArgument
from redbot.core.i18n import Translator

_ = Translator("Cleanup", __file__)


class RawMessageIds(Converter):
    async def convert(self, ctx, argument):
        if argument.isnumeric() and len(argument) >= 17:
            return int(argument)

        raise BadArgument(
            _("{} doesn't look like a valid message ID.").format(argument)
        )
