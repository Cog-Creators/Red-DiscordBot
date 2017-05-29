from core import sentry_setup


def test_sentry_capture():
    sentry_setup.init_sentry_logging()

    assert sentry_setup.client is not None

    sentry_setup.client.captureMessage("Message from test_sentry module.")