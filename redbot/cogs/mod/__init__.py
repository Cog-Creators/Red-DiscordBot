from redbot.core.bot import Red
from .modcore import Mod


def setup(bot: Red):
    bot.add_cog(Mod(bot))
