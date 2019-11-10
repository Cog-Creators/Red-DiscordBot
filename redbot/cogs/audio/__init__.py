# -*- coding: utf-8 -*-
# Red Imports
from redbot.core import commands

# Red Relative Imports
from .audio import Audio


def setup(bot: commands.Bot):
    cog = Audio(bot)
    bot.add_cog(cog)
