"""Errors module for the commands package."""
import inspect
import discord
from discord.ext import commands

__all__ = ["ConversionFailure", "BotMissingPermissions"]


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
