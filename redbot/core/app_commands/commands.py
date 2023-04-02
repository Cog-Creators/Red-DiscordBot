from discord.app_commands import (
    Command as DPYCommand,
    ContextMenu as DPYContextMenu,
    Group as DPYGroup,
)
from discord.utils import MISSING, _shorten

import inspect
from typing import Any, Dict

__all__ = (
    "Command",
    "command",
)

class Command(DPYCommand):
    """
    Command class for Red.

    This class inherits from `discord.app_commands.Command`. The
    attributes listed below are simply additions to the ones listed
    with that class.

    .. warning::

        If you subclass this command, attributes and methods
        must remain compatible.
        None of your methods should start with ``red_`` or
        be dunder names which start with red (eg. ``__red_test_thing__``)
        unless to override behavior in a method designed to be overridden,
        as this prefix is reserved for future methods in order to be
        able to add features non-breakingly.

    Attributes
    ----------
    red_force_enable : bool
        Whether this command should be forced to be enabled at all times.
        Warning: This will cause your cog to fail to load if adding the
        command would put the bot over the command limits.
    """
    def __init__(self, *args, **kwargs):
        self.red_force_enable = kwargs.pop("red_force_enable", False)
        super().__init__(*args, **kwargs)
    
    def _copy_with(self, *args, **kwargs):
        """Add Red's extra attributes to copies."""
        new_copy = super()._copy_with(*args, **kwargs)
        new_copy.red_force_enable = self.red_force_enable
        return new_copy


class ContextMenu(DPYContextMenu):
    """
    ContextMenu class for Red.

    This class inherits from `discord.app_commands.ContextMenu`. The
    attributes listed below are simply additions to the ones listed
    with that class.

    .. warning::

        If you subclass this command, attributes and methods
        must remain compatible.
        None of your methods should start with ``red_`` or
        be dunder names which start with red (eg. ``__red_test_thing__``)
        unless to override behavior in a method designed to be overridden,
        as this prefix is reserved for future methods in order to be
        able to add features non-breakingly.

    Attributes
    ----------
    red_force_enable : bool
        Whether this command should be forced to be enabled at all times.
        Warning: This will cause your cog to fail to load if adding the
        command would put the bot over the command limits.
    """
    def __init__(self, *args, **kwargs):
        self.red_force_enable = kwargs.pop("red_force_enable", False)
        super().__init__(*args, **kwargs)


class Group(DPYGroup):
    """
    Group class for Red.

    This class inherits from `discord.app_commands.Group`. The
    attributes listed below are simply additions to the ones listed
    with that class.

    .. warning::

        If you subclass this command, attributes and methods
        must remain compatible.
        None of your methods should start with ``red_`` or
        be dunder names which start with red (eg. ``__red_test_thing__``)
        unless to override behavior in a method designed to be overridden,
        as this prefix is reserved for future methods in order to be
        able to add features non-breakingly.

    Attributes
    ----------
    red_force_enable : bool
        Whether this command should be forced to be enabled at all times.
        Warning: This will cause your cog to fail to load if adding the
        command would put the bot over the command limits.
    """
    def __init__(self, *args, **kwargs):
        self.red_force_enable = kwargs.pop("red_force_enable", False)
        super().__init__(*args, **kwargs)
    
    def _copy_with(self, *args, **kwargs):
        """Add Red's extra attributes to copies."""
        new_copy = super()._copy_with(*args, **kwargs)
        new_copy.red_force_enable = self.red_force_enable
        return new_copy

    def command(
        self,
        *,
        name: str = MISSING,
        description: str = MISSING,
        nsfw: bool = False,
        auto_locale_strings: bool = True,
        extras: Dict[Any, Any] = MISSING,
    ):
        """
        A decorator which transforms an async function into a `Command` that is a subcommand of this group.

        Same interface as `discord.app_commands.Group.command`.
        """
        def decorator(func):
            if not inspect.iscoroutinefunction(func):
                raise TypeError('command function must be a coroutine function')

            if description is MISSING:
                if func.__doc__ is None:
                    desc = '\N{HORIZONTAL ELLIPSIS}'
                else:
                    desc = _shorten(func.__doc__)
            else:
                desc = description

            command = Command(
                name=name if name is not MISSING else func.__name__,
                description=desc,
                callback=func,
                nsfw=nsfw,
                parent=self,
                auto_locale_strings=auto_locale_strings,
                extras=extras,
                red_force_enable=self.red_force_enable,
            )
            self.add_command(command)
            return command

        return decorator


def command(
    *,
    name: str = MISSING,
    description: str = MISSING,
    nsfw: bool = False,
    auto_locale_strings: bool = True,
    extras: Dict[Any, Any] = MISSING,
    red_force_enable: bool = False,
):
    """
    A decorator which transforms an async function into a `Command`.

    Same interface as `discord.app_commands.command`.
    """
    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise TypeError('command function must be a coroutine function')

        if description is MISSING:
            if func.__doc__ is None:
                desc = '\N{HORIZONTAL ELLIPSIS}'
            else:
                desc = _shorten(func.__doc__)
        else:
            desc = description

        return Command(
            name=name if name is not MISSING else func.__name__,
            description=desc,
            callback=func,
            parent=None,
            nsfw=nsfw,
            auto_locale_strings=auto_locale_strings,
            extras=extras,
            red_force_enable=red_force_enable,
        )

    return decorator


def context_menu(
    *,
    name: str = MISSING,
    nsfw: bool = False,
    auto_locale_strings: bool = True,
    extras: Dict[Any, Any] = MISSING,
    red_force_enable: bool = False,
):
    """
    A decorator which transforms an async function into a `ContextMenu`.

    Same interface as `discord.app_commands.context_menu`.
    """

    def decorator(func):
        if not inspect.iscoroutinefunction(func):
            raise TypeError('context menu function must be a coroutine function')

        actual_name = func.__name__.title() if name is MISSING else name
        return ContextMenu(
            name=actual_name,
            nsfw=nsfw,
            callback=func,
            auto_locale_strings=auto_locale_strings,
            extras=extras,
            red_force_enable=red_force_enable,
        )

    return decorator
