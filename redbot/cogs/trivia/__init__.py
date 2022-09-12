"""Package for Trivia cog."""
from redbot.core.bot import Red

from .trivia import InvalidListError, Trivia, get_core_lists, get_list

__all__ = (
    "InvalidListError",
    "get_core_lists",
    "get_list",
)


async def setup(bot: Red) -> None:
    """Load Trivia."""
    await bot.add_cog(Trivia(bot))
