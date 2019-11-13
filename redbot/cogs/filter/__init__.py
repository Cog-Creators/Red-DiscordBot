from redbot.core.bot import Red

from .filter import Filter


def setup(bot: Red):
    bot.add_cog(Filter(bot))
