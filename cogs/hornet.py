import discord
from discord.ext import commands

class Hornet:
    """Post Hornet"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def hornet(self, ctx):
        """GIT GUD"""
        with open('data/resources/hornet.png', 'rb') as f:
            await self.bot.send_file(ctx.message.channel, f)

def setup(bot):
    bot.add_cog(Hornet(bot))

