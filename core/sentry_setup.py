from raven import Client
from raven.versioning import fetch_git_sha
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

from pathlib import Path


client = None


def init_sentry_logging():
    global client
    client = Client(
        dsn=("https://27f3915ba0144725a53ea5a99c9ae6f3:87913fb5d0894251821dcf06e5e9cfe6@"
             "sentry.telemetry.red/19?verify_ssl=0"),
        include_paths=(
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
        ),
        release=fetch_git_sha(str(Path.cwd()))
    )

    handler = SentryHandler(client)
    setup_logging(
        handler,
        exclude=(
            "asyncio",
            "discord"
        )
    )
