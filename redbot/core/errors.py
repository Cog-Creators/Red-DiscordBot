import importlib.machinery
from typing import Optional
from unittest import mock

import discord
from aiohttp import ClientResponse
from aiohttp.helpers import TimerNoop
from yarl import URL

from .i18n import Translator

_ = Translator(__name__, __file__)

__all__ = (
    "RedError",
    "PackageAlreadyLoaded",
    "CogLoadError",
    "BankError",
    "BalanceTooHigh",
    "PreventedAPIException",
)

_FakeResponseObject = ClientResponse(
    "get",
    URL("https://example.org"),
    request_info=mock.Mock(),
    writer=mock.Mock(),
    continue100=None,
    timer=TimerNoop(),
    traces=[],
    loop=mock.Mock(),
    session=mock.Mock(),
)

_FakeResponseObject.status = 403


class RedError(Exception):
    """Base error class for Red-related errors."""


class PackageAlreadyLoaded(RedError):
    """Raised when trying to load an already-loaded package."""

    def __init__(self, spec: importlib.machinery.ModuleSpec, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spec: importlib.machinery.ModuleSpec = spec

    def __str__(self) -> str:
        return f"There is already a package named {self.spec.name.split('.')[-1]} loaded"


class CogLoadError(RedError):
    """Raised by a cog when it cannot load itself.
    The message will be send to the user."""

    pass


class BankError(RedError):
    """Base error class for bank-related errors."""


class BalanceTooHigh(BankError, OverflowError):
    """Raised when trying to set a user's balance to higher than the maximum."""

    def __init__(
        self, user: discord.abc.User, max_balance: int, currency_name: str, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.user = user
        self.max_balance = max_balance
        self.currency_name = currency_name

    def __str__(self) -> str:
        return _("{user}'s balance cannot rise above {max:,} {currency}.").format(
            user=self.user, max=self.max_balance, currency=self.currency_name
        )


class PreventedAPIException(RedError, discord.Forbidden):
    """
    Raised when Red detects an attempt to do something which would cause a 403
    
    This exists due to new autoban thresholds which were implemented on 2019-08-11
    These thresholds are being tightended on 2019-09-10

    Initial threshold: 25,000 bad calls per hour
    Enhanced threshold 10,000 bad calls per hour

    The bad calls in this case are any calls which generate these http codes:
        401
        403
        429

    The status codes and thresholds for this are subject to change.
    No code should rely on these, just avoid causing them where possible.

    Currently, there is no confirmation on excluding blocked user 403's from this limit.
    We may need to account for this in some places in code.

    The following are discord specific codes which are not detectable in advance, but are
    403 HTTP Exceptions.
    
        Blocked reaction discord error code: 90001
        Cannot DM user (blocked or closed DMs) discord error code: 50007
    
    Last updated for accuracy: 2019-08-13
    """

    def __init__(self, message=""):
        super().__init__(_FakeResponseObject, message)
        self.code = -26
        self.text = ""
