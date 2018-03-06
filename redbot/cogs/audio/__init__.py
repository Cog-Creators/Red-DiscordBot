from .audio import Audio
from discord.ext import commands


async def setup(bot: commands.Bot):
    cog = Audio(bot)
    await cog.init_config()
    bot.add_cog(cog)
