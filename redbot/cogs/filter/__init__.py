from .filter import Filter
from redbot.core.bot import Red


async def setup(bot: Red) -> None:
    cog = Filter(bot)
    await cog.initialize()
    bot.add_cog(cog)
