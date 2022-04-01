from typing import NewType, TYPE_CHECKING

from bluebot.core.commands import BadArgument
from bluebot.core.i18n import Translator
from bluebot.core.utils.chat_formatting import inline

_ = Translator("Economy", __file__)

# But I'm smarter than most of these boulderheads and you know it!
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
