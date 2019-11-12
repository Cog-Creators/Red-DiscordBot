# -*- coding: utf-8 -*-
# Red Imports
from redbot.core.bot import Red

# Red Relative Imports
from .mod import Mod


async def setup(bot: Red):
    cog = Mod(bot)
    await cog.initialize()
    bot.add_cog(cog)
