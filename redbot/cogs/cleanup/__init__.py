from .cleanup import Cleanup
from redbot.core.bot import Red


def setup(bot: Red):
    bot.add_cog(Cleanup(bot))
