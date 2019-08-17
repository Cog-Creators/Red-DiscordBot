from redbot.core import commands

from .audio import Audio


async def setup(bot: commands.Bot):
    cog = Audio(bot)
    await cog.initialize()
    bot.add_cog(cog)
