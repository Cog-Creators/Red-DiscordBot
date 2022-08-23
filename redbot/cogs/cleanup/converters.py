from typing import NewType, TYPE_CHECKING

from redbot.core.commands import BadArgument, Context, Converter
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import inline

_ = Translator("Cleanup", __file__)

SNOWFLAKE_THRESHOLD = 2**63


class RawMessageIds(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        if argument.isnumeric() and len(argument) >= 17 and int(argument) < SNOWFLAKE_THRESHOLD:
            return int(argument)

        raise BadArgument(_("{} doesn't look like a valid message ID.").format(argument))


PositiveInt = NewType("PositiveInt", int)
if TYPE_CHECKING:
    positive_int = PositiveInt
else:

    def positive_int(arg: str) -> int:
        try:
            ret = int(arg)
        except ValueError:
            raise BadArgument(_("{arg} is not an integer.").format(arg=inline(arg)))
        if ret <= 0:
            raise BadArgument(_("{arg} is not a positive integer.").format(arg=inline(arg)))
        return ret
