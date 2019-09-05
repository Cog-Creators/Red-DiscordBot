# Red Imports
from redbot.core.bot import Red

# Red Relative Imports
from .filter import Filter


def setup(bot: Red):
    bot.add_cog(Filter(bot))
