from .alias import Alias
from redbot.core.bot import Red


def setup(bot: Red):
    bot.add_cog(Alias(bot))
