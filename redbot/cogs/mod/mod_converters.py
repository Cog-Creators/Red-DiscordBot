import argparse
from typing import Tuple, Optional
from datetime import timedelta

import discord
from redbot.core.commands import MemberConverter, timedelta_converter, Context, BadArgument

__all__ = ["mute_converter"]


class NoExitArgparse(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument(None, None)


def mute_converter(argument: str) -> Tuple[Optional[str], Optional[timedelta]]:
    """
    Valid uses:
        User
        -t [timedelta]
        --reason being an ass
        -r timeout --timed 1hr
    """
    mute_parser = NoExitArgparse(description="Mute Parser", add_help=False, allow_abbrev=True)
    mute_parser.add_argument("--reason", "-r", nargs="*", dest="reason", default="")
    mute_parser.add_argument("--timed", "-t", nargs="*", dest="timed", default="")
    vals = mute_parser.parse_args(argument.split())
    reason = " ".join(vals.reason) or None
    time_interval = timedelta_converter((" ".join(vals.timed))) if vals.timed else None
    return reason, time_interval
