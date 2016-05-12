import discord
from discord.ext import commands
from __main__ import send_cmd_help

#A pull request is pending for the BeautifulSoup warning: https://github.com/goldsmith/Wikipedia/pull/112
#If you receiving this error and don't want to wait for the fix to be merged in to the wikipedia module, you could fix it manually.
#
#\Python35\Lib\site-packages\wikipedia\wikipedia.py@line 389
#Change:
#   lis = BeautifulSoup(html).find_all('li')  
#To:
#   lis = BeautifulSoup(html, "html.parser").find_all('li')

class Wikipedia:
    """Wikipedia search for the Red-DiscordBot"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def wikipedia(self, ctx, *text):
        """Wikipedia search."""     

        if text == ():
            await send_cmd_help(ctx)
            return
        else:            
            s = "_";
            search = ""
            search = s.join(text)
            user = ctx.message.author
            wikiLang = 'en'# Define the Wikipedia language / Most of these are supported » https://nl.wikipedia.org/wiki/ISO_3166-1
            ws = None
            wikipedia.set_lang(wikiLang)# Set the Wikipedia language.
            try:
                ws = wikipedia.page(search)
                wikiUrl = (ws.url.encode('ascii', 'xmlcharrefreplace'))
                await self.bot.say(wikiUrl.decode("utf8"))
            except:
                await self.bot.say( 'Sorry {}, no wiki hit, try to rephrase'.format(user))

class ModuleNotFound(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message
        
def setup(bot):
    global wikipedia
    try:
        import wikipedia
    except:
        raise ModuleNotFound("Wikipedia is not installed. Do 'pip3 install wikipedia --upgrade' to use this cog.")
    bot.add_cog(Wikipedia(bot))



