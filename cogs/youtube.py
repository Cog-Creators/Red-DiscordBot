from discord.ext import commands
import aiohttp
import re


class YouTube:
    """Le YouTube cog."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['yt'])
    async def youtube(self, context, *arguments: str):
        """Search on Youtube"""
        try:
            url = 'https://www.youtube.com/results?'
            payload = {'search_query': " ".join(arguments)}
            headers = {'user-agent': 'Red-cog/1.0'}
            conn = aiohttp.TCPConnector(verify_ssl=False)
            session = aiohttp.ClientSession(connector=conn)
            async with session.get(url, params=payload, headers=headers) as r:
                result = await r.text()
            session.close()
            yt_find = re.findall(r'href=\"\/watch\?v=(.{11})', result)
            message = 'https://www.youtube.com/watch?v={}\n'.format(yt_find[0])
        except Exception as e:
            message = 'Something went terribly wrong! [{}]'.format(e)
        await self.bot.say(message)


def setup(bot):
    bot.add_cog(YouTube(bot))
