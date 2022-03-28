from redbot.core.bot import Blue
from .modlog import ModLog


def setup(bot: Blue):
    bot.add_cog(ModLog(bot))
