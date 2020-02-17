from __future__ import annotations

"""
This contains specific event loop handling for various use cases in red

This module is private, and for internal use only.
"""

import asyncio
import contextlib
import logging
import types
import sys
import os
import gc
from typing import Optional


if sys.implementation.name == "cpython":
    try:
        import uvloop
    except ImportError:
        uvloop = None
    else:
        uvloop.install()


def windows_issues_are_fun(loop: asyncio.AbstractEventLoop, log: Optional[logging.Logger] = None):
    """

    Related to: BPO-39232

        Below are comments from Sinbad (mikeshardmind). Do not modify these comments.
        #
        # I apologize for the below.
        # This is some of the ugliest, jankiest shit I've ever written.
        # I started to look into a suitable fix for this to PR to cpython,
        # but the scope of a fix quickly looked like something I could not PR
        # without further discussion with a python core developer, as it would
        # actually require changing the design of the proactor event loop
        # significantly. This is't something I'm interested in putting my time
        # into as there has been no response from anyone who has worked on this
        # and my personal investment in improving the proactor event loop is
        # extremely limited.
        #
        # Until then, we're doing some *very* ugly things here.

    This should only be called on a loop which will not be re-used afterward.
    This bypasses a safety check on the loop for a specific case.
    This bypass is relatively safe, but *only* if the loop won't be re-used.
    """
    gc.collect()

    if log and log.isEnabledFor(logging.DEBUG):
        log.warning(
            "Patching for BPO-39232."
            " If this line occurs prior to application teardown process,"
            " things will break."
        )

    def _our_check_closed(self):
        if log and log.isEnabledFor(logging.DEBUG):
            log.info("Loop is closed. (BPO-39232 workaround applied)")

    # This really shouldn't be neccessary, but:
    #   1. GC is non-deterministic
    #   2. the proactor event loop's ordering of events is non deterministic
    #       (relying on notify-complete of Windows IOCP)
    #   3. it's an error to do certain things with the loop being closed
    #   4. when transports are no longer needed (via __del__) they schedule cleanup on the loop
    #   5. Uncatchable runtime error on windows with the proactor event loop.
    loop._check_closed = types.MethodType(_our_check_closed, loop)


def cleanup_event_loop(loop: asyncio.AbstractEventLoop, log: Optional[logging.Logger] = None):

    if loop.is_running():
        raise RuntimeError("Loop must not be running to start cleanup.")

    if os.name == "nt":
        windows_issues_are_fun(loop, log)

    loop.run_until_complete(loop.shutdown_asyncgens())

    if log:
        log.info("Please wait, cleaning up a bit more")
    loop.run_until_complete(asyncio.sleep(2))
    asyncio.set_event_loop(None)
    loop.stop()
    loop.close()


@contextlib.contextmanager
def new_main_event_loop(log: Optional[logging.Logger] = None):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield loop
    finally:
        cleanup_event_loop(loop, log)
