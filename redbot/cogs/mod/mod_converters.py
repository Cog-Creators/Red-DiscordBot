import argparse
import shlex
from typing import Tuple, Optional
from datetime import timedelta

import discord
from redbot.core.commands import MemberConverter, timedelta_converter, Context, BadArgument

__all__ = ["mute_converter"]

mute_parser = argparse.ArgumentParser(
    description="Mute Parser",
    add_help=False,
    allow_abbrev=True,
    usage="redbot <member> [arguments]",
)
mute_parser.add_argument("--reason", nargs="*", dest="reason", default="")
mute_parser.add_argument("--timed", nargs="*", dest="timed", default="")
mute_parser.add_argument("--for", nargs="*", dest="timed", default="")


def mute_converter(argument: str) -> Tuple[Optional[str], Optional[timedelta]]:
    """
    Valid uses:
        User
        -t [timedelta]
        --reason being an ass
        -r timeout --timed 1hr
        --reason needs to cool off --for 3 hours
    """
    vals = mute_parser.parse_args(shlex.split(argument))
    reason = vals.reason or None
    time_interval = timedelta_converter(vals.timed) if vals.timed else None
    return reason, time_interval
