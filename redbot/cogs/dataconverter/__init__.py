from redbot.core.bot import Red
from .dataconverter import DataConverter


async def setup(bot: Red):
    await bot.add_cog(DataConverter(bot))
