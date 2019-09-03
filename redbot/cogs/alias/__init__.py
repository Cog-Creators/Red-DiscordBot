from redbot.core.bot import Red
from .alias import Alias


def setup(bot: Red):
    bot.add_cog(Alias(bot))
