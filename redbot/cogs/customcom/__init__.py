# Red Relative Imports
from .customcom import CustomCommands


def setup(bot):
    bot.add_cog(CustomCommands(bot))
