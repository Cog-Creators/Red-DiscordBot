"""Package for Trivia cog."""
from .trivia import Trivia


def setup(bot):
    """Load Trivia."""
    cog = Trivia()
    bot.add_cog(cog)
