from .utils.dataIO import fileIO    # will break soon™    # will break soon™  
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
#PREFIXES = bot_settings.prefixes~~~~~~

class imdb:
    """Myapifilms.com imdb movie search."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO(SETTINGS, "load")    # will break soon™    # will break soon™  
        if self.settings["api_key"] == "":
            print("Cog error: imdb, No API key found, please configure me!")

    @commands.command(pass_context=True, no_pm=True)
    async def imdb(self, ctx, *title):
        """Search for movies on imdb"""
        if title == ():
            await send_cmd_help(ctx)
            return
        else:
            if self.settings["api_key"] == "":
                getKeyUrl = "http://www.myapifilms.com/token.do"
                await self.bot.say("` This cog wasn't configured properly. If you're the owner, add your API key available from '{}', and use '{}apikey_imdb' to setup`".format(getKeyUrl, "p"))
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
                    urlz = result['data']['movies'][0]['urlIMDB']
                    urlPoster = result['data']['movies'][0]['urlPoster']
                    if urlPoster == "": urlPoster = "http://instagram.apps.wix.com/bundles/wixinstagram/images/ge/no_media.png"
                    simplePlot = result['data']['movies'][0]['simplePlot']
                    if simplePlot == "": simplePlot = "Everyone died...."


                #data = discord.Embed(colour=discord.Colour.yellow())
                data = discord.Embed(colour=0xE4BA22)
                data.add_field(name="Title:", value=str(title), inline=True)
                data.add_field(name="Released on:", value=year)

                if rating != "-":
                    emoji = ":poop:"
                    if float(rating) > 3.5:
                        emoji = ":thumbsdown:"
                    if float(rating) > 5.2:
                        emoji = ":thumbsup:"
                    if float(rating) > 7.0:
                        emoji = ":ok_hand:"
                else:
                    emoji = ""
                rating = "{} {}".format(rating, emoji)
                data.add_field(name="IMDB Rating:", value=rating)


                if urlz != "":
                    moreinfo = ("{}\n[Read more...]({})".format(simplePlot, urlz))
                    data.add_field(name="Plot:", value=moreinfo)
                data.set_footer(text='\n\n*Respond now with "cover" for a bigger image')
                data.set_thumbnail(url=urlPoster)
                await self.bot.say(embed=data)

                #Big image, will break soon™
                find = "._V1_";
                split_pos = urlPoster.find(find)
                urlPoster = urlPoster[0:split_pos+5]+".jpg"

                response = await self.bot.wait_for_message(timeout=20, author=ctx.message.author)
                if response is None:
                    pass
                else:
                    response = response.content.lower().strip()
                if response.startswith(("bigpic", "cover", "big", ":eyeglasses:")):
                    await self.bot.say(urlPoster)
            except discord.HTTPException:
                await self.bot.say("I need the `Embed links` permission to send this")
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
                fileIO(SETTINGS, "save", self.settings)    # will break soon™    # will break soon™    # will break soon™    # will break soon™    # will break soon™  
                await self.bot.say("{} ` imdb API key saved...`".format(user.mention))
            else:
                await self.bot.say("{} `Cancled API key opertation...`".format(user.mention))
        else:
            self.settings["api_key"] = key
            fileIO(SETTINGS, "save", self.settings)
            await self.bot.say("{} ` imdb API key saved...`".format(user.mention))
        self.settings = fileIO(SETTINGS, "load")    # will break soon™    # will break soon™    # will break soon™    # will break soon™

def check_folders():
    if not os.path.exists(DIR_DATA):
        print("Creating data/imdb folder...")
        os.makedirs(DIR_DATA)

def check_files():
    settings = {"api_key": ""}

    # will break soon™
    if not fileIO(SETTINGS, "check"):
        print("Creating settings.json")
        fileIO(SETTINGS, "save", settings)    # will break soon™      # will break soon™      # will break soon™      # will break soon™  

def setup(bot):
    check_folders()
    check_files()
    n = imdb(bot)
    bot.add_cog(n)

