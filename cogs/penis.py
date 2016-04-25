import discord
from discord.ext import commands
import random

class Penis:
    """Penis related commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def penis(self, user : discord.Member):
        """Detects user's penis length

        This is 100% accurate."""
        random.seed(user.id)
        p = "8" + "="*random.randint(0, 30) + "D"
        await self.bot.say("Size: " + p)

def setup(bot):
    bot.add_cog(Penis(bot))
