from redbot.core.bot import Red
from .mod import Mod


def setup(bot: Red):
    bot.add_cog(Mod(bot))
