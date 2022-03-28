from .cleanup import Cleanup
from bluebot.core.bot import Blue


def setup(bot: Blue):
    bot.add_cog(Cleanup(bot))
