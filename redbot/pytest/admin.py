from unittest.mock import MagicMock

import pytest

from redbot.cogs.admin import Admin
from redbot.cogs.admin.announcer import Announcer


@pytest.fixture()
def admin(config):
    return Admin(config)


@pytest.fixture()
def announcer(admin):
    a = Announcer(MagicMock(), "Some message", admin.conf)
    yield a
    a.cancel()