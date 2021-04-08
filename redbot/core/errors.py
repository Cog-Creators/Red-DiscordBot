import importlib.machinery

import discord

from redbot.core.utils.chat_formatting import humanize_number
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
    The message will be sent to the user."""

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
        return _("{user}'s balance cannot rise above {max} {currency}.").format(
            user=self.user, max=humanize_number(self.max_balance), currency=self.currency_name
        )


class BankPruneError(BankError):
    """Raised when trying to prune a local bank and no server is specified."""


class MissingExtraRequirements(RedError):
    """Raised when an extra requirement is missing but required."""


class ConfigError(RedError):
    """Error in a Config operation."""


class StoredTypeError(ConfigError, TypeError):
    """A TypeError pertaining to stored Config data.

    This error may arise when, for example, trying to increment a value
    which is not a number, or trying to toggle a value which is not a
    boolean.
    """


class CannotSetSubfield(StoredTypeError):
    """Tried to set sub-field of an invalid data structure.

    This would occur in the following example::

        >>> import asyncio
        >>> from redbot.core import Config
        >>> config = Config.get_conf(None, 1234, cog_name="Example")
        >>> async def example():
        ...     await config.foo.set(True)
        ...     await config.set_raw("foo", "bar", False)  # Should raise here
        ...
        >>> asyncio.run(example())

    """


class MuteError(RedError):
    """Base error class for Mute-related errors."""
    def __init__(self, **kwargs):
        self.member = kwargs.get("member")
        self.reason = kwargs.get("reason")
        self.guild = kwargs.get("guild")
        self.channel = kwargs.get("channel")
        self.channels = kwargs.get("channels")


class MuteRoleMissingError(MuteError):
    """Raised if role mutes are set and the role is missing."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MuteAdministratorError(MuteError):
    """Raised when mute was called on an administrator."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MuteHierarchyError(MuteError):
    """Raised when mute was called on someone higher in the role hierarchy."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MuteRoleHierarchyError(MuteError):
    """Raised when there is a role hierarchy issue."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MutePermissionError(MuteError):
    """Raised when mute was called without proper channel permissions."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MuteMissingChannelError(MuteError):
    """Raised when the channel a user should be muted in is missing."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MuteVoicePermissionError(MuteError):
    """
    Raised when we failed to move the user into their current  voice
    channel to apply mute overwrites.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MuteLeftGuildError(MuteError):
    """
    Raised when we the member has already left the guild.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MuteAlreadyUnMutedError(MuteError):
    """
    Raised when the member is already unmuted in a channel.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
