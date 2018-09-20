import re
from datetime import timedelta
from redbot.core.commands import BadArgument

__all__ = ["timedelta_converter"]

# I could keep this one long string, but this is much easier to read/extend.
TIME_RE_STRING = r"\s?".join(
    [
        r"((?P<days>\d+?)\s?(d(ays?)?))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m))?",
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)

TIME_RE = re.compile(TIME_RE_STRING, re.I)


def timedelta_converter(argument: str) -> timedelta:
    """
    Attempts to parse a user input string as a timedelta

    Arguments
    ---------
    argument: str
        String to attempt to treat as a timedelta

    Returns
    -------
    datetime.timedelta
        The parsed timedelta
    
    Raises
    ------
    ~discord.ext.commands.BadArgument
        No time was found from the given string.
    """
    matches = TIME_RE.match(argument)
    params = {k: int(v) for k, v in matches.groupdict().items() if v is not None}
    if not params:
        raise BadArgument("I couldn't turn that into a valid time period.")
    return timedelta(**params)
