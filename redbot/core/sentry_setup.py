from raven import Client
from raven.handlers.logging import SentryHandler

from redbot.core import __version__

__all__ = ("init_sentry_logging",)


include_paths = (
    'redbot',
)

client = None


def init_sentry_logging(logger):
    global client
    client = Client(
        dsn=("https://62402161d4cd4ef18f83b16f3e22a020:9310ef55a502442598203205a84da2bb@"
             "sentry.io/253983"),
        release=__version__,
        include_paths=['redbot'],
        enable_breadcrumbs=False
    )
    handler = SentryHandler(client)
    logger.addHandler(handler)
