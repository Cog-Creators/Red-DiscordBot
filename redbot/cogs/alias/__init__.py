from .alias import Alias
from redbot.core.bot import Red


async def setup(bot: Red) -> None:
    cog = Alias(bot)
    await bot.add_cog(cog)
    cog.sync_init()
