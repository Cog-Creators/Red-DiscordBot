from redbot.core.bot import Red

from .reports import Reports


def setup(bot: Red):
    bot.add_cog(Reports(bot))
