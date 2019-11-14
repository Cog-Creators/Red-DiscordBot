from redbot.core import commands

from .audio import Audio


def setup(bot: commands.Bot):
    cog = Audio(bot)
    bot.add_cog(cog)
