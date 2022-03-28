from bluebot.core.bot import Blue
from .reports import Reports


def setup(bot: Blue):
    bot.add_cog(Reports(bot))
