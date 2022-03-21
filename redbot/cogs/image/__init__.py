from redbot.core.bot import Red

from .image import Image


async def setup(bot: Red) -> None:
    cog = Image(bot)
    await cog.initialize()
    await bot.add_cog(cog)
