# Red Imports
from redbot.core.bot import Red

# Red Relative Imports
from .economy import Economy


def setup(bot: Red):
    bot.add_cog(Economy(bot))
