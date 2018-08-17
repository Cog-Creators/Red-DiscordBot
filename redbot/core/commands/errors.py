"""Errors module for the commands package."""
import inspect
from discord.ext import commands

__all__ = ["ConversionFailure"]


class ConversionFailure(commands.BadArgument):
    """Raised when converting an argument fails."""

    def __init__(self, converter, argument: str, param: inspect.Parameter, *args):
        self.converter = converter
        self.argument = argument
        self.param = param
        super().__init__(*args)
