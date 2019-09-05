# Red Imports
from redbot.core.bot import Red

# Red Relative Imports
from .reports import Reports


def setup(bot: Red):
    bot.add_cog(Reports(bot))
