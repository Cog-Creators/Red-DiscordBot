import re
from datetime import timedelta
from . import Converter, Context, BadArgument

__all__ = ["Time"]


class Time(Converter):
    """
    Convert to a :class:`datetime.timedelta` class.

    The converter supports seconds, minutes, hours and days.

    Time can be attached to the unit (only use the first letter) or not
    (then use the full word).

    .. admonition:: Example

    *   `50s` = `50 seconds` -> :class:`datetime.timedelta(seconds=50)`
    *   `12m` = `12 minutes` -> :class:`datetime.timedelta(seconds=720)`
    *   `4h` = `4 hours` -> :class:`datetime.timedelta(seconds=14400)`
    *   `1d` = `1 day` -> :class:`datetime.timedelta(days=1)`

    Using the converter with a command:
    .. code-block:: python3

        @commands.command()
        async def timer(self, ctx, time: commands.Time):
            await self.start_timer(time)

    Using the converter manually:
    .. code-block:: python3

        async def convert_time(ctx: RedContext, text: str) -> datetime.timedelta:
            time = await commands.Time.convert(ctx, text)
            return time

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
    """

    async def convert(ctx: Context, argument: str) -> timedelta:
        TIME_RE = re.compile(
            r"((?P<days>\d+?)\s?(d(ays?)?))?\s?((?P<hours>\d+?)\s?(hours?|hrs|hr?))?\s?((?P<minutes>\d+?)\s?(minutes?|mins?|m))?\s?((?P<seconds>\d+?)\s?(seconds?|secs?|s))?\s?",
            re.I,
        )
        matches = TIME_RE.match(argument)
        params = {k: int(v) for k, v in matches.groupdict().items() if None not in (k, v)}
        time = timedelta(**params)
        if str(time) == "0:00:00":
            raise BadArgument("No time could be found.")
        return time
