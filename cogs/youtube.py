from discord.ext import commands
import aiohttp
import discord
import re


class YouTube:
    """Le YouTube Cog"""
    def __init__(self, bot):
        self.bot = bot
        self.youtube_regex = (
          r'(https?://)?(www\.)?'
          '(youtube|youtu|youtube-nocookie)\.(com|be)/'
          '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    @commands.command(pass_context=True, name='youtube', no_pm=True)
    async def _youtube(self, context, *, query: str):
        """Search on Youtube"""
        try:
            url = 'https://www.youtube.com/results?'
            payload = {'search_query': ''.join(query)}
            headers = {'user-agent': 'MARViN-cog/1.0'}
            conn = aiohttp.TCPConnector(verify_ssl=False)
            session = aiohttp.ClientSession(connector=conn)
            async with session.get(url, params=payload, headers=headers) as r:
                result = await r.text()
            session.close()
            yt_find = re.findall(r'href=\"\/watch\?v=(.{11})', result)
            print(result)
            url = 'https://www.youtube.com/watch?v={}'.format(yt_find[0])
            await self.bot.say(url)
        except Exception as e:
            message = 'Something went terribly wrong! [{}]'.format(e)
            await self.bot.say(message)


def setup(bot):
    n = YouTube(bot)
    bot.add_cog(n)
