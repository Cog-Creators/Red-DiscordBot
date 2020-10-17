from typing import NewType, TYPE_CHECKING

from redbot.core.commands import BadArgument, Context, Converter, check
from redbot.core.utils.mod import is_mod_or_superior, check_permissions
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import inline

_ = Translator("Cleanup", __file__)


class RawMessageIds(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        if argument.isnumeric() and len(argument) >= 17:
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


def check_self_permissions():
    async def predicate(ctx: Context):
        if not ctx.guild:
            return True
        if await check_permissions(ctx, {"manage_messages": True}) or await is_mod_or_superior(
            ctx.bot, ctx.author
        ):
            return True
        return False

    return check(predicate)
