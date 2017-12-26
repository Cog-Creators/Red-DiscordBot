import logging

from redbot.core import sentry


def test_sentry_capture(red):
    log = logging.getLogger(__name__)
    mgr = sentry.SentryManager(log)

    assert mgr.client is not None

    mgr.client.captureMessage("Message from test_sentry module.")