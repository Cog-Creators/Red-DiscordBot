"""Package for Trivia cog."""
from .trivia import *
from .session import *
from .log import *


def setup(bot):
    """Load Trivia."""
    cog = Trivia(bot.user.id)
    bot.add_cog(cog)
