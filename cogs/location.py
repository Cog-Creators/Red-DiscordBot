import discord
import json
import requests
from discord.ext import commands
from cogs.utils import checks
import pycountry
import re

class location:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def location(self, ctx, country: str):
        """Example: -location GB"""
        server = ctx.message.server
        user = ctx.message.author
        perms = discord.Permissions.none()

        re1 = '((?:[a-z][a-z]+))'  # Word 1
        re2 = '.*?'  # Non-greedy match on filler
        re3 = '((?:[a-z][a-z]+))'  # Word 2
        rg = re.compile(re1 + re2 + re3, re.IGNORECASE | re.DOTALL)

        m = rg.search(country)
        subregionobj = None
        try:
            if m:
                word1 = m.group(1)
                countryobj = pycountry.countries.get(alpha2=word1.upper())
                subregionobj = pycountry.subdivisions.get(code=country.upper())
            else:
                countryobj = pycountry.countries.get(alpha2=country.upper())
        except:
            countryobj = None
        easter = "shithole";

        if countryobj is not None:
            if subregionobj is not None:
                msg = "All members for " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha2.lower() + ":\n```"
                try:
                    for member in server._members:
                        for role in server._members[member].roles:
                            if subregionobj.code == role.name:
                                msg = msg + "\n• " + server._members[member].name
                    msg = msg + "```"
                    if msg != "All members for " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha2.lower().lower() + ":\n``````":
                        await self.bot.say(msg)
                    else:
                        await self.bot.say(
                            "No one found in " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha2.lower().lower() + ": :(")
                except:
                    await self.bot.say("w00ps, something went wrong! :( Please try again.")
            else:
                msg = "All members for " + countryobj.name + " :flag_"+ countryobj.alpha2.lower() +":\n```"
                try:
                    for member in server._members:
                        for role in server._members[member].roles:
                            if countryobj.name == role.name:
                                msg = msg + "\n• " + server._members[member].name
                    msg = msg + "```"
                    if msg != "All members for " + countryobj.name + " :flag_"+ countryobj.alpha2.lower() +":\n``````":
                        await self.bot.say(msg)
                    else:
                        await self.bot.say("No one found in " + countryobj.name + " :flag_"+ countryobj.alpha2.lower() +": :(")
                except:
                    await self.bot.say("w00ps, something went wrong! :( Please try again.")
        else:
            if country.lower() == easter:
                msg = "All members for SHITHOLE :poop: : \n```•SpiritoftheWest#4290```"
                await self.bot.say(msg)
            else:
                await self.bot.say("Sorry I don't know your country! Did you use the correct ISO countrycode? \nExample: `-location GB`")
def setup(bot):
    bot.add_cog(location(bot))
