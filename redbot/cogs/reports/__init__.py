from redbot.core.bot import Red
from .reports import Reports


async def setup(bot: Red):
    await bot.add_cog(Reports(bot))
