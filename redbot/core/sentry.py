import asyncio
import logging
from raven import Client
from raven.handlers.logging import SentryHandler
from raven_aiohttp import AioHttpTransport

from redbot.core import __version__

__all__ = ("SentryManager",)


class SentryManager:
    """Simple class to manage sentry logging for Red."""

    def __init__(self, logger: logging.Logger):
        self.client = Client(
            dsn=(
                "https://62402161d4cd4ef18f83b16f3e22a020:9310ef55a502442598203205a84da2bb@"
                "sentry.io/253983"
            ),
            release=__version__,
            include_paths=["redbot"],
            enable_breadcrumbs=False,
            transport=AioHttpTransport,
        )
        self.handler = SentryHandler(self.client)
        self.logger = logger

    def enable(self):
        """Enable error reporting for Sentry."""
        self.logger.addHandler(self.handler)

    def disable(self):
        """Disable error reporting for Sentry."""
        self.logger.removeHandler(self.handler)
        loop = asyncio.get_event_loop()
        loop.create_task(self.close())

    async def close(self):
        """Wait for the Sentry client to send pending messages and shut down."""
        await self.client.remote.get_transport().close()
