import discord
from discord.ext import commands
import requests
import re

class YouTube:
    """Le YouTube cog."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['yt'])
    async def youtube(self, context, *arguments : str):
        """Search on Youtube"""
        payload = {'search_query' : " ".join(arguments)}
        headers = {'user-agent': 'Multivac/1.0.1'}
        request = requests.get('https://www.youtube.com/results?', headers=headers, params=payload)
        results = re.findall(r'href=\"\/watch\?v=(.{11})', request.text)
        message ='https://www.youtube.com/watch?v={0}\n'.format(results[0])
        await self.bot.say(message)

def setup(bot):
    bot.add_cog(YouTube(bot))