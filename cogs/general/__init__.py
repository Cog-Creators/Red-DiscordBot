from .general import General


def setup(bot):
    n = General(bot)
    bot.add_cog(n)
