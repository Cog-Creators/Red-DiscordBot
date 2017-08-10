from .economy import Economy
from core.bot import Red


def setup(bot: Red):
    bot.add_cog(Economy(bot))
