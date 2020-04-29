from redbot.core.bot import Red
from .mod import Mod


async def setup(bot: Red):
    cog = Mod(bot)
    bot.add_cog(cog)
    await cog.initialize()
