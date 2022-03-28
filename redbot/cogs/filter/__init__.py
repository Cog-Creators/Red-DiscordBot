from .filter import Filter
from bluebot.core.bot import Blue


async def setup(bot: Blue) -> None:
    cog = Filter(bot)
    await cog.initialize()
    bot.add_cog(cog)
