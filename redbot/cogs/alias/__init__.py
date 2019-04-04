from .alias import Alias
from redbot.core.bot import Red


async def setup(bot: Red):
    await bot.add_cog(Alias(bot))
