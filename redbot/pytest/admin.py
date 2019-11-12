# -*- coding: utf-8 -*-
# Standard Library
from unittest.mock import MagicMock

# Red Dependencies
import pytest

# Red Imports
from redbot.cogs.admin import Admin
from redbot.cogs.admin.announcer import Announcer

__all__ = ["admin", "announcer"]


@pytest.fixture()
def admin(config):
    return Admin(config)


@pytest.fixture()
def announcer(admin):
    a = Announcer(MagicMock(), "Some message", admin.conf)
    yield a
    a.cancel()
