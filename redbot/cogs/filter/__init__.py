from .filter import Filter
from redbot.core.bot import Red


async def setup(bot: Red):
    await bot.add_cog(Filter(bot))
