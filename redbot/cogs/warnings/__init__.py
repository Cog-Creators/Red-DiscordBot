from redbot.core.bot import Red

from .warnings import Warnings


async def setup(bot: Red) -> None:
    cog = Warnings(bot)
    await cog.initialize()
    bot.add_cog(cog)
