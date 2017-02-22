import discord
from discord.ext import commands
import aiohttp
import json

class Fortune:
    """It's time to get your fortune"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def fortune(self, ctx):
        """Fortune Time"""
        
        user = ctx.message.author
        link = "https://helloacm.com/api/fortune/"
        headers = {'user-agent': 'MARViN-cog/1.0'}
        conn = aiohttp.TCPConnector(verify_ssl=False)
        session = aiohttp.ClientSession(connector=conn)
        async with aiohttp.get(link, headers=headers) as m:
            result = await m.json()
            fortune = discord.Embed(colour=user.colour)
            fortune.add_field(name="{}'s Fortune!:smiley:".format(user.name),value="{}".format(result))
            await self.bot.say(embed=fortune)

def setup(bot):
    bot.add_cog(Fortune(bot))
