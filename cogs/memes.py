import discord
from discord.ext import commands

class Memes:
    """Post Image Memes"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def hornet(self, ctx):
        """GIT GUD"""
        with open('data/resources/hornet.png', 'rb') as f:
            await self.bot.send_file(ctx.message.channel, f)

    @commands.command(pass_context=True)
    async def yay(self, ctx):
        """doens't count"""
        with open('data/resources/doenst.png', 'rb') as f:
            await self.bot.send_file(ctx.message.channel, f)

    @commands.command(pass_context=True)
    async def nugs(self, ctx):
        """Absolute garbage"""
        with open('data/resources/nugs.jpg', 'rb') as f:
            await self.bot.send_file(ctx.message.channel, f)

def setup(bot):
    bot.add_cog(Memes(bot))

