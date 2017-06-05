import discord
import json
import requests
import re
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
        self.valid = "^[0123456789p{L} _.]+$abcdefghijklmnopqrstuvwxyz"
        self.apikey = "b096f8311a7c35406547e0b38363f0ee"
        self.rapikey = "RGAPI-e807e69e-4f64-455c-9654-49caca7e2b08"
        self.people = {'justin': 'jhin','minseong': 'ahri','james': 'caitlyn','david': 'darius', 'jp': 'yorick', 'mark': 'nidalee','frank': 'ekko','corey': 'khazix', 'amit': 'zed', 'kevin': 'akali', 'devon': 'shaco', 'vinh': 'riven', 'andrew':'katarina', 'nigger': 'urgot', 'leo': 'yasuo', 'bill': 'janna', 'jihad':'ziggs'}

    @commands.command()
    async def winrate(self,*,name):
        """Tells you the winrate of one champion and gives it a Devon rating"""
        if name.lower() == "suicide":
            await self.bot.say("Suicides's winrate is 100%. That's a 7/7 on the Justin scale.")
        else:
            if name.lower() in self.people.keys():
                name = self.people[name.lower()]

            print("[Champgg] FINDING WINRATE OF " + name)
            cname = name.upper()[0] + name[1:]
            name = name.replace(" ","")


            url = "http://api.champion.gg/champion/" + name + "/general?api_key=" + self.apikey  # build the web adress

            request = requests.get(url)
            data = request.json()
            try:
                winpercent = float(data[0]['winPercent']['val'])
            except:
                await self.bot.say("Can't find any data for " + cname)
                return

            if  winpercent < 50.0:
                if winpercent < 45.0:
                    rating = -1
                else:
                    rating = 0
            else:
                rating = int((winpercent - 50))

            if rating == -1:
                await self.bot.say(cname + '\'s winrate is ' + str(winpercent) + "%. That will not be touched by Devon.")
            else:
                await self.bot.say(cname + '\'s winrate is ' + str(winpercent) + "%. That's a " + str(rating) + "/7 on the Devon scale.")

    @commands.command()
    async def jhinrate(self):
        """Tells you the jhinrate"""
        name = "jhin"

        url = "http://api.champion.gg/champion/" + name + "/general?api_key=" + self.apikey  # build the web adress

        request = requests.get(url)
        data = request.json()

        try:
            await self.bot.say("The current jhinrate is " + str(float(data[0]['winPercent']['val'])) + "%.")
        except:
            await self.bot.say("Can't find any data for " + name)
            return
    @commands.command()
    async def id(self, *, name):
        """Tells you the ID of a player"""
        if(special_match(name)):
            cname = name
            name = name.replace(" ", "")
            name = name.lower()

            print(name)

            url = "https://na.api.pvp.net/api/lol/na/v1.4/summoner/by-name/" + name + "?api_key=" + self.rapikey  # build the web adress

            #print("[Champgg] FINDING WINRATE OF " + name + url)
            request = requests.get(url)
            data = request.json()
            try:
                id = data[name]['id']
            except:
                await self.bot.say("Can't find any data for " + cname)
                return

            url = "https://na.api.pvp.net/api/lol/na/v1.3/stats/by-summoner/"+ str(id) + "/summary"  # build the web adress

            await self.bot.say(cname + '\'s ID is ' + str(id) + ".")
        else:
            await self.bot.say("Invalid name.")

    @commands.command()
    async def icanprobablygetrank1(self, *, name):
        """Who doesn't want to be RRRRRRRRRANK 1??"""
        if(special_match(name)):
            cname = name
            name = name.replace(" ", "")
            name = name.lower()

            print(name)

            url = "https://na.api.pvp.net/api/lol/na/v2.5/league/challenger?type=RANKED_SOLO_5x5&api_key=" + self.rapikey  # build the web adress

            #print("[Champgg] FINDING WINRATE OF " + name + url)
            request = requests.get(url)
            data = request.json()
            try:
                await self.bot.say("~~~~~~2020 CHALLENGER LEADERBOARDS~~~~~~~~~~~~~~")
                await self.bot.say("1. " + name)
                for i in range(1,5):
                    await self.bot.say(str(i+1) + ". " + data['entries'][i]['playerOrTeamName'])
            except:
                await self.bot.say("No data!")
                return
        else:
            await self.bot.say("Invalid name.")

    @commands.command(pass_context=True)
    async def pullup(self, ctx, user: discord.Member):
        """PULL UP ON @USER >.<"""

        # Your code will go here
        await self.bot.say("BANG BANG! Yung " + ctx.message.author.mention + " just pulled up on " + user.mention + " ! :open_mouth: :open_mouth: :gun: :gun:")

def special_match(strg, search=re.compile(r'[^\. a-z0-9A-Z]').search):
    return not bool(search(strg))
def setup(bot):
    if soupAvailable:
        bot.add_cog(Champgg(bot))
    else:
        raise RuntimeError("You need to run `pip3 install beautifulsoup4`")
