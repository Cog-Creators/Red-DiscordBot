"""Package for Trivia cog."""
from redbot.core.bot import Red
from .trivia import Trivia


def setup(bot: Red):
    """Load Trivia."""
    cog = Trivia(bot)
    bot.add_cog(cog)
