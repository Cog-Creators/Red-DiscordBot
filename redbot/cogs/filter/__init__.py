from redbot.core.bot import Red

from .filter import Filter


async def setup(bot: Red) -> None:
    await bot.add_cog(Filter(bot))
