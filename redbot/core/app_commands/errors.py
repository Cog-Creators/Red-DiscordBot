"""Errors module for the app_commands package."""
from discord import app_commands

__all__ = ("UserFeedbackCheckFailure",)


class UserFeedbackCheckFailure(app_commands.CheckFailure):
    """A generic version of CheckFailure."""

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(message, *args)
