import logging

import click

IS_DEBUG = False


@click.group(invoke_without_command=True)
@click.option("--debug", type=bool)
@click.pass_context
def cli(ctx, debug):
    """Create a new instance."""
    global IS_DEBUG
    IS_DEBUG = debug


def is_debug() -> bool:
    return IS_DEBUG


def debug_exc_log(lg: logging.Logger, exc: Exception, msg: str = None):
    if lg.getEffectiveLevel() <= logging.DEBUG:
        if msg is None:
            msg = f"{exc}"
        lg.exception(msg, exc_info=exc)
