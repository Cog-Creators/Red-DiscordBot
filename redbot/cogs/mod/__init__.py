from redbot.core.bot import Red
from .mod import Mod


async def setup(bot: Red):
    await bot.add_cog(Mod(bot))
