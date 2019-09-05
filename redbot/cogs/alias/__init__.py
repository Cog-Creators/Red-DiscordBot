# Red Imports
from redbot.core.bot import Red

# Red Relative Imports
from .alias import Alias


def setup(bot: Red):
    bot.add_cog(Alias(bot))
