from raven import Client, breadcrumbs
from raven.handlers.logging import SentryHandler

from redbot.core import __version__

__all__ = ("init_sentry_logging", "should_log")


include_paths = (
    'core',
    'cogs.alias',
    'cogs.audio',
    'cogs.downloader',
    'cogs.economy',
    'cogs.general',
    'cogs.image',
    'cogs.streams',
    'cogs.trivia',
    'cogs.utils',
    'tests.core.test_sentry',
    'main',
    'launcher'
)

client = None


def init_sentry_logging(logger):
    global client
    client = Client(
        dsn=("https://c44012bfbdfb4002b6025936bb91696d:14f35ce5db344cd083506c628b9a146c@"
             "sentry.io/253980"),
        release=__version__
    )

    breadcrumbs.ignore_logger("websockets")
    breadcrumbs.ignore_logger("websockets.protocol")
    handler = SentryHandler(client)
    logger.addHandler(handler)


def should_log(module_name: str) -> bool:
    return any(module_name.startswith(path) for path in include_paths)
