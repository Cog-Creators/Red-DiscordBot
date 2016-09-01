import discord
import json
from datetime import datetime, timedelta
import pytz
import googlemaps as googlemaps
import requests
from discord.ext import commands
from cogs.utils import checks
import pycountry
import re
from __main__ import send_cmd_help
from pytz import country_timezones


class timezone:
    def __init__(self, bot):
        self.bot = bot
        self.gmaps = googlemaps.Client(key='AIzaSyAUO8P24PsGAAJpr7e4N3pL9Mhx6qL4YNs')
        self.utc = pytz.utc

    async def timecheck(self, code: str):
        fmt = '%H:%M'
        geocode_result = self.gmaps.geocode(code)
        timezone_result = self.gmaps.timezone(geocode_result[0]['geometry']['location'])
        local = pytz.timezone(timezone_result['timeZoneId'])
        utc_dt = datetime.now(tz=self.utc)
        time = utc_dt.astimezone(local)
        await self.bot.say(
            "Its currently " + time.strftime(fmt) + " in " + geocode_result[0]['formatted_address'] + "!")

    @commands.group(pass_context=True)
    async def localtime(self, ctx):
        """General time stuff."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @localtime.command(name="location", pass_context=True)
    async def location(self, ctx, location: str = ""):
        """Example: -localtime <ISO Code>"""
        re1 = '((?:[a-z][a-z]+))'  # Word 1
        re2 = '.*?'  # Non-greedy match on filler
        re3 = '((?:[a-z][a-z]+))'  # Word 2
        rg = re.compile(re1 + re2 + re3, re.IGNORECASE | re.DOTALL)

        m = rg.search(location)
        subregionobj = None
        try:
            if m:
                word1 = m.group(1)
                countryobj = pycountry.countries.get(alpha2=word1.upper())
                subregionobj = pycountry.subdivisions.get(code=location.upper())
            else:
                countryobj = pycountry.countries.get(alpha2=location.upper())
        except:
            countryobj = None
        if countryobj is not None:
            if subregionobj is not None:
                await self.timecheck(subregionobj.code)
            else:
                await self.timecheck(countryobj.alpha2)
        else:
            await self.bot.say(
                "Sorry I don't know your country! Did you use the correct ISO countrycode? \nExample: `-time GB`\n`-time US-CA`")

    @localtime.command(name="user",pass_context=True)
    async def time(self, ctx, user: discord.Member = None):
        """Example: -localtime @user"""
        author = ctx.message.author
        subregionobj = None
        countryobj = None
        if not user:
            user = author
        for role in user.roles:
            try:
                subregionobj = pycountry.subdivisions.get(code=role.name)
                countryobj = subregionobj.country
                break
            except:
                subregionobj = None
                continue
        if subregionobj is None:
            for role in user.roles:
                try:
                    if role.permissions.value == 0:
                        countryobj = pycountry.countries.get(name=role.name)
                        break
                except:
                    continue

        if countryobj is not None:
            if subregionobj is not None:
                await self.timecheck(subregionobj.code)
            else:
                await self.timecheck(countryobj.name)
        else:
            await self.bot.say(
                "Sorry I don't know the country of the user! Is the country set in the profile?")

def setup(bot):
    bot.add_cog(timezone(bot))
