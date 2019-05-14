from redbot.core.commands import Converter, BadArgument
from redbot.core.i18n import Translator

_ = Translator("Mod", __file__)


class RawUserIds(Converter):
    async def convert(self, ctx, argument):
        # This is for the hackban command, where we receive IDs that
        # are most likely not in the guild.
        # As long as it's numeric and long enough, it makes a good candidate
        # to attempt a ban on
        if argument.isnumeric() and len(argument) >= 17:
            return int(argument)

        raise BadArgument(_("{} doesn't look like a valid user ID.").format(argument))
