# Red Imports
from redbot.core.bot import Red

# Red Relative Imports
from .modlog import ModLog


def setup(bot: Red):
    bot.add_cog(ModLog(bot))
