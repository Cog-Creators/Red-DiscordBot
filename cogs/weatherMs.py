import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
#Sys
import aiohttp
import asyncio
import json
import os


SETTINGS = "data/weather/settings.json"

class weatherMs:
    """Search for weather in given location."""

    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/weather/settings.json", "load")
                
    @commands.command(no_pm=True, pass_context=False)
    async def temp(self, location, country: str=None):
        """Make sure to get your own API key and put it into data/weather/settings.json
        \nYou can get an API key from: www.wunderground.com/weather/api/"""
        if country is None:
            country = self.settings["defCountry"]
        url = "http://api.wunderground.com/api/" + self.settings['api_key'] + "/conditions/q/" + country + "/" + location +".json"
        async with aiohttp.get(url) as r:
            data = await r.json()
        if "current_observation" in data:
            tempCO = data["current_observation"].get("temperature_string", False)
            tempW = data["current_observation"].get("weather", " ")
            tempC = data["current_observation"].get("temp_c", " ")
            tempF = data["current_observation"].get("temp_f", " ")
            tempH = data["current_observation"].get("relative_humidity", " ")
            if tempCO != False:
                if self.settings["unit"] == "C": 
                    await self.bot.say("**Weather **{} **Temp.** {}{} **Hum. **{} ".format(tempW, str(tempC), u"\u2103", tempH))
                elif self.settings["unit"] == "F":    
                    await self.bot.say("**Weather **{} **Temp.** {}F **Hum. **{} ".format(tempW, str(tempF), tempH))
            else:
                await self.bot.say("No temperature found")
        else:
            await self.bot.say("`Please use a US zip code or format like: paris fr\nIf the default country is set to your requesting location just '!temp city' will do.\nThe the default country is set to: {} `".format(self.settings["defCountry"]))

    @commands.command(pass_context=True, no_pm=False)
    @checks.admin_or_permissions(manage_server=True)
    async def toggleunit(self, ctx):
        """Switches the default unit: Celcius/Farherheit.
        Admin/owner restricted."""
        user= ctx.message.author        
        if self.settings["unit"] == "C":
            self.settings["unit"] = "F"
            allowBot = "Farhenheit"
        elif self.settings["unit"] == "F":
            self.settings["unit"] = "C"
            allowBot = "Celcius"
        await self.bot.say("{} ` The default unit is now: {}.`".format(user.mention, allowBot))       
        fileIO(SETTINGS, "save", self.settings)
        
    @commands.command(pass_context=True, no_pm=False)
    @checks.admin_or_permissions(manage_server=True)
    async def setcountry(self, ctx, country):
        """Sets the default country/zip code.
        Admin/owner restricted."""
        user= ctx.message.author        
        if country is None:
            await self.bot.say("{} ` tell me: {}.`".format(user.mention, country))    
        else:
            self.settings["defCountry"] = country
            await self.bot.say("{} ` The default country is now: {}.`".format(user.mention, country))       
        fileIO(SETTINGS, "save", self.settings)        
            
def check_folders():
    if not os.path.exists("data/weather"):
        print("Creating data/weather folder...")
        os.makedirs("data/weather")

def check_files():
    settings = {"api_key": "Get your API key from: www.wunderground.com/weather/api/", "unit": "C", "defCountry": "uk" }
    
    if not fileIO(SETTINGS, "check"):
        print("Creating settings.json")
        print("You must obtain an API key as noted in the newly created 'settings.json' file")
        fileIO(SETTINGS, "save", settings)

def setup(bot):
    check_folders()
    check_files()
    n = weatherMs(bot)
    bot.add_cog(n)
