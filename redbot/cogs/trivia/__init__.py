"""Package for Trivia cog."""

from .log import *
from .session import *
from .trivia import *


def setup(bot):
    """Load Trivia."""
    cog = Trivia()
    bot.add_cog(cog)
