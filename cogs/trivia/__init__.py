"""Package for Trivia cog."""
from core.bot import Red
from .trivia import Trivia

def setup(bot: Red):
    """Load Trivia."""
    cog = Trivia(bot)
    bot.add_listener(cog.end_session, "on_trivia_end")
    bot.add_cog(cog)
