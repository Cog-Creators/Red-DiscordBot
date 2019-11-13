from redbot.core.bot import Red

from .cleanup import Cleanup


def setup(bot: Red):
    bot.add_cog(Cleanup(bot))
