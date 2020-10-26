from redbot.core.bot import Red
from .mutes import Mutes


async def setup(bot: Red):
    cog = Mutes(bot)
    bot.add_cog(cog)
    await cog.initialize()
