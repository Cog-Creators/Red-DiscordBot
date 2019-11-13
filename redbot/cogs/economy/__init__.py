from redbot.core.bot import Red

from .economy import Economy


def setup(bot: Red):
    bot.add_cog(Economy(bot))
