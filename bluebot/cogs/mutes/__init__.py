from bluebot.core.bot import Blue
from .mutes import Mutes


def setup(bot: Blue):
    cog = Mutes(bot)
    bot.add_cog(cog)
