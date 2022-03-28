from bluebot.core.bot import Blue
from .mod import Mod


async def setup(bot: Blue):
    cog = Mod(bot)
    bot.add_cog(cog)
    await cog.initialize()
