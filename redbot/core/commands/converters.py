import re
from datetime import timedelta
from typing import TYPE_CHECKING

from redbot.core.commands import Converter, BadArgument

if TYPE_CHECKING:
    from .commands import Context

TIME_RE = re.compile(
    r"((?P<days>\d+?)\s?(d(ays?)?))?\s?((?P<hours>\d+?)\s?(hours?|hrs|hr?))?\s?((?P<minutes>\d+?)\s?(minutes?|mins?|m))?\s?((?P<seconds>\d+?)\s?(seconds?|secs?|s))?\s?",
    re.I,
)


class TimedeltaConverter(Converter):
    """
    Convert to a :class:`datetime.timedelta` class.

    The converter supports seconds, minutes, hours and days.

    Time can be attached to the unit (only use the first letter) or not
    (then use the full word).

    .. admonition:: Example

        *   ``50s`` = ``50 seconds`` -> :class:`datetime.timedelta(seconds=50)`
        *   ``12m`` = ``12 minutes`` -> :class:`datetime.timedelta(seconds=720)`
        *   ``4h`` = ``4 hours`` -> :class:`datetime.timedelta(seconds=14400)`
        *   ``1d`` = ``1 day`` -> :class:`datetime.timedelta(days=1)`

        Using the converter with a command:

        .. code-block:: python3

            @commands.command()
            async def timer(self, ctx, time: commands.TimedeltaConverter):
                await asyncio.sleep(time.total_seconds())
                await ctx.send("Time's up!")

        Using the converter manually:

        .. code-block:: python3

            async def convert_time(ctx: Context, text: str) -> datetime.timedelta:
                time = await commands.TimedeltaConverter().convert(ctx, text)
                return time
    """

    async def convert(self, ctx: "Context", argument: str) -> timedelta:
        """
        Manually convert a string to a :class:`datetime.timedelta` class.

        .. warning:: This should not be called as a command function annotation.
            This is for manual calls.

        Arguments
        ---------
        ctx: Context
            The context of the command.
        argument: str
            The string you want to convert.

        Returns
        -------
        datetime.timedelta
            The :class:`datetime.timedelta` object.

        Raises
        ------
        ~discord.ext.commands.BadArgument
            No time was found from the given string.
        """
        matches = TIME_RE.match(argument)
        params = {k: int(v) for k, v in matches.groupdict().items() if None not in (k, v)}
        if not params:
            raise BadArgument("No time could be found.")
        time = timedelta(**params)
        return time
