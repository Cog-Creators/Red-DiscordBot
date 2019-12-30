from .streams import Streams


async def setup(bot):
    cog = Streams(bot)
    bot.add_cog(cog)
