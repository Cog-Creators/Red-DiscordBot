import discord
import json
import requests
from discord.ext import commands
from cogs.utils import checks
import pycountry
import re


class countrycode:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def country(self, ctx, country: str):
        """Example: -country GB"""
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
            countryobj= None

        if countryobj is not None:
            try:
                if subregionobj is not None:
                    if subregionobj.code not in [r.name for r in server.roles]:
                        await self.bot.create_role(server, name=subregionobj.code, permissions=perms)
                        await self.bot.say("Added " + subregionobj.code + " to country list!")
                    role = discord.utils.get(ctx.message.server.roles, name=subregionobj.code)
                    if subregionobj.code not in [r.name for r in user.roles]:
                        await self.bot.add_roles(user, role)
                        await self.bot.say(
                            "Greetings from " + countryobj.name + ": " + subregionobj.name + " :flag_" + countryobj.alpha2.lower() + ": by " + user.mention)
                    else:
                        await self.bot.say("You already set your countryorigin to that country!")
                else:
                    if (countryobj.name) not in [r.name for r in server.roles]:
                        await self.bot.create_role(server, name=countryobj.name, permissions=perms)
                        await self.bot.say("Added " + countryobj.name + " to country list!")
                    role = discord.utils.get(ctx.message.server.roles, name=countryobj.name)
                    if countryobj.name not in [r.name for r in user.roles]:
                        await self.bot.add_roles(user, role)
                        await self.bot.say(
                            "Greetings from " + countryobj.name + " :flag_" + countryobj.alpha2.lower() + ": by " + user.mention)
                    else:
                        await self.bot.say("You already set your countryorigin to that country!")
            except AttributeError:
                await self.bot.say("w00ps, something went wrong! :( Please try again.")
        else:
            await self.bot.say(
                "Sorry I don't know your country! Did you use the correct ISO countrycode? \nExample: `-country GB`")

    @commands.command(pass_context=True, no_pm=True)
    async def removecountry(self, ctx, country: str):

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
            countryobj= None
        # try:
        if countryobj is not None:
            if subregionobj is not None:
                if subregionobj.code not in [r.name for r in server.roles]:
                    await self.bot.create_role(server, name=subregionobj.code, permissions=perms)
                r = discord.utils.get(ctx.message.server.roles, name=subregionobj.code)
                if subregionobj.code in [r.name for r in user.roles]:
                    await self.bot.remove_roles(user, r)
                    await self.bot.say(
                        "The boys and girls from " + countryobj.name + ": " + subregionobj.name + " will miss you " + user.mention + "! :(")
                else:
                    await self.bot.say("You already removed that country as your countryorigin!")
            else:
                if countryobj.name not in [r.name for r in server.roles]:
                    await self.bot.create_role(server, name=countryobj.name, permissions=perms)
                r = discord.utils.get(ctx.message.server.roles, name=countryobj.name)
                if countryobj.name in [r.name for r in user.roles]:
                    await self.bot.remove_roles(user, r)
                    await self.bot.say(
                        "The boys and girls from " + countryobj.name + " will miss you " + user.mention + "! :(")
                else:
                    await self.bot.say("You already removed that country as your countryorigin!")
        else:
            await self.bot.say("Sorry I don't know your country! Did you use the correct ISO countrycode?")


def setup(bot):
    bot.add_cog(countrycode(bot))
