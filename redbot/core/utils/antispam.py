from datetime import datetime, timedelta
from typing import Tuple, List
from collections import namedtuple

Interval = Tuple[timedelta, int]
AntiSpamInterval = namedtuple("AntiSpamInterval", ["period", "frequency"])


class AntiSpam:
    """
    Custom class which is more flexible than using discord.py's
    `commands.cooldown()`

    Can be intialized with a custom set of intervals
    These should be provided as a list of tuples in the form
    (timedelta, quantity)

    Where quantity represents the maximum amount of times
    something should be allowed in an interval.
    """

    # TODO : Decorator interface for command check using `spammy`
    # with insertion of the antispam element into context
    # for manual stamping on succesful command completion

    default_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 10),
        (timedelta(days=1), 24),
    ]

    def __init__(self, intervals: List[Interval]):
        self.__event_timestamps = []
        _itvs = intervals if intervals else self.default_intervals
        self.__intervals = [AntiSpamInterval(*x) for x in _itvs]
        self.__discard_after = max([x.period for x in self.__intervals])

    def __interval_check(self, interval: AntiSpamInterval):
        return (
            len([t for t in self.__event_timestamps if (t + interval.period) > datetime.utcnow()])
            >= interval.frequency
        )

    @property
    def spammy(self):
        """
        use this to check if any interval criteria are met
        """
        return any(self.__interval_check(x) for x in self.__intervals)

    def stamp(self):
        """
        Use this to mark an event that counts against the intervals
        as happening now
        """
        self.__event_timestamps.append(datetime.utcnow())
        self.__event_timestamps = [
            t for t in self.__event_timestamps if t + self.__discard_after > datetime.utcnow()
        ]
