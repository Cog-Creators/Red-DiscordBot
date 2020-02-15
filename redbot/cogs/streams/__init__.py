from .streams import Streams


def setup(bot):
    cog = Streams(bot)
    bot.add_cog(cog)
