import discord
from discord.ext import commands
import asyncio
import random

class Russian:
    """HE'S FROM RUSSIA!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def russian(self):
        """WE NEED MORE RUSSIA IN CHAT!"""

        await self.bot.say("PUTIN VODKA BALALAIKA!\nhttps://s-media-cache-ak0.pinimg.com/736x/64/84/bb/6484bbae1782cc50059be379254c7e77.jpg")

def setup(bot):
    bot.add_cog(Russian(bot))
