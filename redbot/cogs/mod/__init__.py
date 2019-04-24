from redbot.core.bot import Red
from .mod import Mod


async def setup(bot: Red):
    cog = Mod(bot)
    await cog.initialize()
    bot.add_cog(cog)
