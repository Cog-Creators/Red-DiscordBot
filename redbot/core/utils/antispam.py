from datetime import datetime, timedelta
from typing import Tuple, List
from collections import namedtuple

Interval = Tuple[timedelta, int]
AntiSpamInterval = namedtuple("AntiSpamInterval", ["period", "frequency"])


class AntiSpam:
    """
    An object that counts against intervals to prevent spam.
    
    Attributes
    ----------
    intervals : List[Tuple[timedelta, int]]
        A list of tuples, where the first item of the tuple is
        a timedelta representing the length of the interval,
        and the second is an int representing the number of repeats
        this interval can have before expiring.
    """

    # TODO : Decorator interface for command check using `spammy`
    # with insertion of the antispam element into context
    # for manual stamping on successful command completion

    default_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 10),
        (timedelta(days=1), 24),
    ]

    def __init__(self, intervals: List[Interval]):
        self.__event_timestamps = []
        _itvs = intervals or self.default_intervals
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
        Check whether any intervals are active.
        """
        return any(self.__interval_check(x) for x in self.__intervals)

    def stamp(self):
        """
        Mark an event against the intervals.
        """
        self.__event_timestamps.append(datetime.utcnow())
        self.__event_timestamps = [
            t for t in self.__event_timestamps if t + self.__discard_after > datetime.utcnow()
        ]
