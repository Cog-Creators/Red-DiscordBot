import discord
import json
import requests
from discord.ext import commands
import aiohttp
try: # check if BeautifulSoup4 is installed
	from bs4 import BeautifulSoup
	soupAvailable = True
except:
	soupAvailable = False

class Champgg:
    """My custom cog that does stuff!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def winrate(self,*,name):
        """Tells you the winrate of one champiion"""
        print("[Champgg] FINDING WINRATE OF " + name)
        name = name.replace(" ","")
        cname = name.upper()[0] + name[1:]

        url = "http://api.champion.gg/champion/" + name + "/general?api_key=b096f8311a7c35406547e0b38363f0ee"  # build the web adress

        request = requests.get(url)
        data = request.json()
        try:
            await self.bot.say(cname + '\'s winrate is ' + str(data[0]['winPercent']['val']) + "%.")
        except:
            await self.bot.say("Can't find any data for " + cname)

def setup(bot):
    if soupAvailable:
        bot.add_cog(Champgg(bot))
    else:
        raise RuntimeError("You need to run `pip3 install beautifulsoup4`")
