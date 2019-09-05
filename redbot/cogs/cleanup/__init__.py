# Red Imports
from redbot.core.bot import Red

# Red Relative Imports
from .cleanup import Cleanup


def setup(bot: Red):
    bot.add_cog(Cleanup(bot))
