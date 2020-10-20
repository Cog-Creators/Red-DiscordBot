from .streams import Streams


def setup(bot):
    cog = Streams(bot)
    bot.add_cog(cog)


def teardown(bot):
    cog = bot.get_cog("Streams")
    cog.cog_unload()
