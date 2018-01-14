from .streams import Streams


def setup(bot):
    bot.add_cog(Streams(bot))
