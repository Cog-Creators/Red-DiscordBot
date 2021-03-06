from .alias import Alias
from redbot.core.bot import Red


async def setup(bot: Red):
    cog = Alias(bot)
    bot.add_cog(cog)
    cog.sync_init()
