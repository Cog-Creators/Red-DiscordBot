"""Package for Trivia cog."""
import logging
from core.bot import Red
from .trivia import Trivia

LOG = logging.getLogger("red.trivia")

def setup(bot: Red):
    """Load Trivia."""
    bot.add_cog(Trivia(bot))
