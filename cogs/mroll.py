import discord
from discord.ext import commands
from random import randint

class MRoll:
    """Roll multiple dice"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def mroll(self, ctx, nSides : int = 100, nDice : int = 1):
        """Rolls random dice.

        nSides - The number of sides on the dice. Defaults to 100.
        nDice - The number of dice to roll. Defaults to 1.

        Example: "mroll 6 2" rolls two 6-sided dice
        """
        author = ctx.message.author
        
        if nDice >= 1:
            if nSides > 1:
                total = 0
                for dieIdx in range(nDice):
                    total += randint(1, nSides)
                return await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, str(total)))
            else:
                return await self.bot.say("{} Maybe higher than 1? ;P".format(author.mention))
        else:
            return await self.bot.say("{} You need to roll at least one die.".format(author.mention))

def setup(bot):
    bot.add_cog(MRoll(bot))