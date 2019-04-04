from redbot.core.bot import Red
from .modlog import ModLog


async def setup(bot: Red):
    await bot.add_cog(ModLog(bot))
