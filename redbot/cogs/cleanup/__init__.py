from .cleanup import Cleanup
from redbot.core.bot import Blue


def setup(bot: Blue):
    bot.add_cog(Cleanup(bot))
