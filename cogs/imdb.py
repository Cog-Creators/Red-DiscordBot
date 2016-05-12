from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
# Sys.
import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
import os

DIR_DATA = "data/imdb"
SETTINGS = DIR_DATA+"/settings.json"

class imdb:
    """Myapifilms.com imdb movie search."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO(SETTINGS, "load")
        if self.settings["api_key"] == "":
            print("Cog error: imdb, No API key found, please configure me!")
        self.PREFIXES = bot_settings.prefixes            

    @commands.command(pass_context=True, no_pm=True)
    async def imdb(self, ctx, *title):
        """Search for movies on imdb"""
        if title == ():
            await send_cmd_help(ctx)
            return
        else:
            if self.settings["api_key"] == "":
                getKeyUrl = "http://www.myapifilms.com/token.do"
                await self.bot.say("` This cog wasn't configured properly. If you're the owner, add your API key available from '{}', and use '{}apikey_imdb' to setup`".format(getKeyUrl, self.PREFIXES[0]))
                return
            try:
                await self.bot.send_typing(ctx.message.channel)
                movieTitle = "+".join(title)
                search = "http://api.myapifilms.com/imdb/title?format=json&title=" + movieTitle + "&token=" + self.settings["api_key"]
                async with aiohttp.get(search) as r:
                    result = await r.json()
                    title = result['data']['movies'][0]['title']
                    year = result['data']['movies'][0]['year']
                    if year == "": year = "????"
                    rating = result['data']['movies'][0]['rating']
                    if rating == "": rating = "-"
                    url = result['data']['movies'][0]['urlIMDB']
                    msg = "**Title:**  {} ** Released on:**  {} ** IMDB Rating:**  {}\n{}".format(title, year, rating, url)
                    await self.bot.say(msg)
            except Exception as e:
                await self.bot.say("` Error getting a result.`")

    @commands.command(pass_context=True, no_pm=False)
    @checks.admin_or_permissions(manage_server=True)
    async def apikey_imdb(self, ctx, key):
        """Set the imdb API key."""
        user = ctx.message.author
        if self.settings["api_key"] != "":
            await self.bot.say("{} ` imdb API key found, overwrite it? y/n`".format(user.mention))
            response = await self.bot.wait_for_message(author=ctx.message.author)
            if response.content.lower().strip() == "y":
                self.settings["api_key"] = key
                fileIO(SETTINGS, "save", self.settings)
                await self.bot.say("{} ` imdb API key saved...`".format(user.mention))
            else:
                await self.bot.say("{} `Cancled API key opertation...`".format(user.mention))
        else:
            self.settings["api_key"] = key
            fileIO(SETTINGS, "save", self.settings)
            await self.bot.say("{} ` imdb API key saved...`".format(user.mention))
        self.settings = fileIO(SETTINGS, "load")            
                
def check_folders():
    if not os.path.exists(DIR_DATA):
        print("Creating data/imdb folder...")
        os.makedirs(DIR_DATA)

def check_files():
    settings = {"api_key": ""}

    if not fileIO(SETTINGS, "check"):
        print("Creating settings.json")
        fileIO(SETTINGS, "save", settings)

def setup(bot):
    check_folders()
    check_files()
    n = imdb(bot)
    bot.add_cog(n)

