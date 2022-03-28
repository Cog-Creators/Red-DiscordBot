from bluebot.core.bot import Blue

from .core import Audio


def setup(bot: Blue):
    cog = Audio(bot)
    bot.add_cog(cog)
    cog.start_up_task()
