from redbot.core.bot import Red
from .economy import Economy


async def setup(bot: Red):
    await bot.add_cog(Economy(bot))
