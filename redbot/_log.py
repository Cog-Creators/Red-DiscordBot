import logging as _logging

__ALL__ = ["VERBOSE", "TRACE", "RedTraceLogger"]

VERBOSE = _logging.DEBUG - 3
TRACE = _logging.DEBUG - 5


class RedTraceLogger(_logging.getLoggerClass()):
    def __init__(self, name, level=_logging.NOTSET):
        super().__init__(name, level)

        _logging.addLevelName(VERBOSE, "VERBOSE")
        _logging.addLevelName(TRACE, "TRACE")

    def verbose(self, msg, *args, **kwargs):
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)

    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)
