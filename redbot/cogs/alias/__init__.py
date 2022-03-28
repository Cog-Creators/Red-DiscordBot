from .alias import Alias
from redbot.core.bot import Blue


async def setup(bot: Blue):
    cog = Alias(bot)
    bot.add_cog(cog)
    cog.sync_init()
