import importlib.machinery
from typing import Optional

import discord

from .i18n import Translator

_ = Translator(__name__, __file__)


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


class FilterError(RedError):
    """Base error class for filter-related errors."""


class InvalidTarget(FilterError, TypeError):
    """Raised when trying to create a filter for something other than a guild or text channel."""

    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target

    def __str__(self) -> str:
        return _(
            "Filter target must be either `discord.Guild` or `discord.TextChannel, not {target}"
        ).format(target=self.target)


class FilterAlreadyExists(FilterError):
    def __init__(self, text, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text
        self.target = target

    def __str__(self) -> str:
        return _("Filter `{filter}` already exists for {target}").format(
            filter=self.text, target=self.target
        )


class NonExistentFilter(FilterError):
    def __init__(self, text, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text
        self.target = target

    def __str__(self) -> str:
        return _("Filter `{filter}` doesn't exist for {target}").format(
            filter=self.text, target=self.target
        )
