from .alias import Alias
from redbot.core.bot import Red


async def setup(bot: Red):
    cog = Alias(bot)
    await cog.initialize()
    bot.add_cog(cog)
