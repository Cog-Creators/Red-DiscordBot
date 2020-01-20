from redbot.core.bot import Red

from .core import Audio


def setup(bot: Red):
    bot.add_cog(Audio(bot))
