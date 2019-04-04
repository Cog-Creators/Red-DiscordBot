"""Package for Trivia cog."""
from .trivia import *
from .session import *
from .log import *


async def setup(bot):
    """Load Trivia."""
    cog = Trivia()
    await bot.add_cog(cog)
