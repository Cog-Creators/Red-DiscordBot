import re
from typing import Tuple, Optional
from datetime import timedelta

import discord

__all__ = ["mute_converter"]


TIMED_MUTE_RE_STRING = r"\s?".join(
    [
        r"((?P<days>\d+?)\s?(d(ays?)?))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m))?",
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
        r"(?P<reason>.+)?",
    ]
)

TIMED_MUTE_RE = re.compile(TIMED_MUTE_RE_STRING, re.I | re.S)


def mute_converter(argument: str) -> Tuple[Optional[str], Optional[timedelta]]:
    """
    Attempts to parse a user input string as a timedelta and/or mod reason

    Arguments
    ---------
    argument: str
        String to attempt to treat as a timedelta and/or mod reason

    Returns
    -------
    Tuple[Optional[str], Optional[datetime.timedelta]]
        The parsed reason and timedelta
    """
    matches = TIMED_MUTE_RE.match(argument)
    params = {k: int(v) for k, v in matches.groupdict().items() if v is not None}
    reason = params.pop("reason", None)
    period = None if not params else timedelta(**params)
    return reason, period
