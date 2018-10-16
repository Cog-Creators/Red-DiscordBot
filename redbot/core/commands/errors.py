"""Errors module for the commands package."""
import inspect
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from .cog import CogMeta

__all__ = ["ConversionFailure", "BotMissingPermissions", "CogError", "OverrideNotAllowed"]


class ConversionFailure(commands.BadArgument):
    """Raised when converting an argument fails."""

    def __init__(self, converter, argument: str, param: inspect.Parameter, *args):
        self.converter = converter
        self.argument = argument
        self.param = param
        super().__init__(*args)


class BotMissingPermissions(commands.CheckFailure):
    """Raised if the bot is missing permissions required to run a command."""

    def __init__(self, missing: discord.Permissions, *args):
        self.missing: discord.Permissions = missing
        super().__init__(*args)


class CogError(Exception):
    """Base exception class for errors relating to cogs."""


class OverrideNotAllowed(CogError):
    """Raised when a cog class tries to override base cog methods.

    Methods and attributes of `commands.Cog` have special meaning and
    should not be overridden.
    """

    def __init__(self, cog_cls: "CogMeta", name: str) -> None:
        self.cog_cls = cog_cls
        self.name = name

    def __str__(self) -> str:
        return f"{self.name} is a reserved cog class attribute"
