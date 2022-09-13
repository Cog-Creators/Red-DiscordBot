from redbot.core.bot import Red

from .cleanup import Cleanup


async def setup(bot: Red) -> None:
    await bot.add_cog(Cleanup(bot))
