from redbot.core.bot import Red

from .alias import Alias


async def setup(bot: Red) -> None:
    await bot.add_cog(Alias(bot))
