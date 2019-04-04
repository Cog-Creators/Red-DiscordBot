from .streams import Streams


async def setup(bot):
    cog = Streams(bot)
    await cog.initialize()
    await bot.add_cog(cog)
