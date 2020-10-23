import logging
import sys

from typing import Final

IS_DEBUG: Final[bool] = "--debug" in sys.argv


def is_debug() -> bool:
    return IS_DEBUG


def debug_exc_log(lg: logging.Logger, exc: Exception, msg: str = None) -> None:
    """Logs an exception if logging is set to DEBUG level"""
    if lg.getEffectiveLevel() <= logging.DEBUG:
        if msg is None:
            msg = f"{exc}"
        lg.exception(msg, exc_info=exc)
