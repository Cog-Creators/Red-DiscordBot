import discord
from discord.ext import commands
import random

class UploadStuff:
    """Upload stuff"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context = True)
    async def upload(self, ctx, stuff):
        """Uploads to channel"""

        await self.bot.send_file(ctx.message.channel, stuff)

def setup(bot):
    bot.add_cog(UploadStuff(bot))
