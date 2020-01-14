import logging
import sys
from typing import NoReturn

IS_DEBUG = "--debug" in sys.argv


def is_debug() -> bool:
    return IS_DEBUG


def debug_exc_log(lg: logging.Logger, exc: Exception, msg: str = None) -> NoReturn:
    if lg.getEffectiveLevel() <= logging.DEBUG:
        if msg is None:
            msg = f"{exc}"
        lg.exception(msg, exc_info=exc)
