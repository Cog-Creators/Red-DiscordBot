# -*- coding: utf-8 -*-
# Red Relative Imports
from .image import Image


async def setup(bot):
    cog = Image(bot)
    await cog.initialize()
    bot.add_cog(cog)
