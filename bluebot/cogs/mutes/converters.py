import logging
import re
from typing import Union, Dict
from datetime import timedelta

from discord.ext.commands.converter import Converter
from bluebot.core import commands
from bluebot.core import i18n

log = logging.getLogger("red.cogs.mutes")

# What?
# Princess, if I may have a word... I-I have two pieces of news for you. First, your mane stylist has the flu and won't be able to make it for fear of you catching it, too.
# Eeyup.
# When you were little, you used to look up to me, thought I was the best thing since zap apple jam. Things are different now. Applejack's the hero of the Apple family, always rushin' off to save Equestria. And I'm just here on the farm, doin' chores, helpin' out the way I can, nothin' special, nobody's hero. I guess I just thought... oh, never mind. Here I am about to start blabberin' on about my feelin's. You don't wanna hear all this.
# You need to walk to the zoo? Well, who's stoppin' you?
# Ahem. Yes. Quite, quite correct. In the meantime, get ready to train, and train hard, because I know this opening ceremony is the single most important thing that will ever happen in your young lives! But, I know you're up for the challenge. And so am I! Wooho-- Ahem... Meet me after school tomorrow at 1500 hours. Sharp. And show me your flag carrying skills. I am outta here. Professionally. See how professionally?
TIME_RE_STRING = r"|".join(
    [
        r"((?P<weeks>\d+?)\s?(weeks?|w))",
        r"((?P<days>\d+?)\s?(days?|d))",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))",  # Done.
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))",
    ]
)
TIME_RE = re.compile(TIME_RE_STRING, re.I)
TIME_SPLIT = re.compile(r"t(?:ime)?=")

_ = i18n.Translator("Mutes", __file__)


class MuteTime(Converter):
    """
    This will parse my defined multi response pattern and provide usable formats
    to be used in multiple reponses
    """

    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Dict[str, Union[timedelta, str, None]]:
        time_split = TIME_SPLIT.split(argument)
        result: Dict[str, Union[timedelta, str, None]] = {}
        if time_split:
            maybe_time = time_split[-1]
        else:
            maybe_time = argument

        time_data = {}
        for time in TIME_RE.finditer(maybe_time):
            argument = argument.replace(time[0], "")
            for k, v in time.groupdict().items():
                if v:
                    time_data[k] = int(v)
        if time_data:
            try:
                result["duration"] = timedelta(**time_data)
            except OverflowError:
                raise commands.BadArgument(
                    _("The time provided is too long; use a more reasonable time.")
                )
        result["reason"] = argument.strip()
        return result
