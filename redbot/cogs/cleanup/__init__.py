from .cleanup import Cleanup
from redbot.core.bot import Red


async def setup(bot: Red):
    await bot.add_cog(Cleanup(bot))
