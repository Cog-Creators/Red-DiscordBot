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
        dsn=("https://62402161d4cd4ef18f83b16f3e22a020:9310ef55a502442598203205a84da2bb@"
             "sentry.io/253983"),
        release=__version__
    )

    breadcrumbs.ignore_logger("websockets")
    breadcrumbs.ignore_logger("websockets.protocol")
    handler = SentryHandler(client)
    logger.addHandler(handler)


def should_log(module_name: str) -> bool:
    return any(module_name.startswith(path) for path in include_paths)
