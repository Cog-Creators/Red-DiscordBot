from .filter import Filter
from redbot.core.bot import Red


def setup(bot: Red):
    bot.add_cog(Filter(bot))
