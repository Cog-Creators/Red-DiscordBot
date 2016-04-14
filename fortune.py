import discord
from discord.ext import commands
from random import randint
from random import choice as randchoice
import random

class Fortune:
    """Fortune Cookie Commands."""

    def __init__(self, bot):
        self.bot = bot
        self.fortune = ["He who laughs at himself never runs out of things to laugh at.","Man who fart in church sit in his own pew",
                        "Man who go to bed with itchy butt wake up with stinky finger", "There is no I in team but U in cunt",
                        "Gay man always order same, Sum Yung Guy", "Man piss in wind, wind piss back"]

    @commands.command(name="fortune", aliases=["cookie"])
    async def _cookie(self):
        """Ask for your fortune

        And look deeply into my scales
        """
        return await self.bot.say("`" + randchoice(self.fortune) + "`")

def setup(bot):
    bot.add_cog(Fortune(bot))
