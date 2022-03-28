from bluebot.core.bot import Blue
from .economy import Economy


def setup(bot: Blue):
    bot.add_cog(Economy(bot))
