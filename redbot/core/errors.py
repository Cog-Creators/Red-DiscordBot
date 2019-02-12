import discord

from .i18n import Translator

_ = Translator(__name__, __file__)


class RedError(Exception):
    """Base error class for Red-related errors."""


class PackageAlreadyLoaded(RedError):
    """Raised when trying to load an already-loaded package."""

    def __init__(self, module_name: str, *args):
        super().__init__(*args)
        self.module_name = module_name

    def __str__(self) -> str:
        return f"There is already a package named {self.module_name} loaded"


class CogLoadError(RedError):
    """Raised by a cog when it cannot load itself.

    The message will be sent to the user.
    """


class NoSuchCog(RedError, ModuleNotFoundError):
    """Thrown when a cog is missing.

    Different from ImportError because some ImportErrors can happen inside cogs.
    """

    def __init__(self, *args, name: str) -> None:
        self.name = name
        super().__init__(*args)


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
