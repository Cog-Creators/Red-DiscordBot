import discord
from discord.ext import commands
import aiohttp

URL = "https://ozdq9jdti1.execute-api.us-east-2.amazonaws.com/prod/getViper"

class RandomFromAlbum:
    """Gets a random image from an Imgur album using an endpoint which returns some JSON"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def viper(self):
        """Posts a viper meme"""
        async with aiohttp.get(URL) as response:
            result = await response.json()
            imageUrl = result["url"]
        await self.bot.say(imageUrl)

def setup(bot):
    bot.add_cog(RandomFromAlbum(bot))

