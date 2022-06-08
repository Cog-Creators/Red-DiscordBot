from datetime import datetime, timedelta
from typing import Tuple, List
from collections import namedtuple

Interval = Tuple[timedelta, int]
AntiSpamInterval = namedtuple("AntiSpamInterval", ["period", "frequency"])


class AntiSpam:
    """
    An object that counts against temporary "intervals"
    to reduce spam. These intervals can be set to incline
    in duration for each interval that is stamped.

    Attributes
    ----------
    intervals : List[Tuple[datetime.timedelta, int]]
        A list of tuples in the format (timedelta, int),
        where the timedelta represents the length of the interval,
        and the int represents the maximum number of times something
        can happen within that interval.
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
        Whether any antispam intervals are active.
        """
        return any(self.__interval_check(x) for x in self.__intervals)

    def stamp(self):
        """
        Mark against the list of antispam intervals.

        The stamp will last until the corresponding interval duration
        has expired (set when this AntiSpam object was initiated).
        """
        self.__event_timestamps.append(datetime.utcnow())
        self.__event_timestamps = [
            t for t in self.__event_timestamps if t + self.__discard_after > datetime.utcnow()
        ]
