import discord
from discord.ext import commands
import asyncio
import random

class Takeover:
    """Takeover another bot"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def Takeover(self, bot):
        """Takes over specified <bot>"""

        await self.bot.say("Possessing control of " + bot + "\n")
        await asyncio.sleep(2)
        await self.bot.say(bot + " awaiting your commands")

def setup(bot):
    bot.add_cog(Takeover(bot))
