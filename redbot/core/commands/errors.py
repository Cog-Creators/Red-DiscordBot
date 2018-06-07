"""Errors module for the commands package."""
from discord.ext import commands

__all__ = ["ConversionFailure"]


class ConversionFailure(commands.BadArgument):
    """Raised when converting an argument fails."""

    def __init__(self, converter, argument: str, *args):
        self.converter = converter
        self.argument = argument
        super().__init__(*args)
