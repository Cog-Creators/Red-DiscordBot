import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from random import randint
from random import choice as randchoice
import os
import re


class Alot:
    """Gives your server invite link to the alots and automatically 
    @mentions them whenever you say their names

    Some alot buddies by:
    SkyOwlKey - That's alot
    Nikki - alot of PR's"""

    # TODO: 
    # o - put data into data file
    # o - turn on per channel
    

    def __init__(self,bot):
        self.bot = bot
        self.numAlotted = 0
        self.alotOfAvatar = "http://static.tvtropes.org/pmwiki/pub/images/alot2258.jpg"
        self.settings = fileIO("data/alot/settings.json", "load")
        alots = fileIO("data/alot/alots.json", "load")
        self.alotTags = alots["TAGS"]
        self.alots = alots["URLS"]
        self.keyRegex = re.compile("\\b"+"("+"|".join(self.alotTags.keys())+")")
        self.alotRegex = re.compile("\\balot\\b")

    @checks.mod_or_permissions(manage_roles=True)
    @commands.command(pass_context=True, no_pm=True)
    async def alot(self, ctx):
        """Lets a lot of alots into this server.
        What's an alot? This is an alot: 
        http://hyperboleandahalf.blogspot.com/2010/04/alot-is-better-than-you-at-everything.html"""
        #default off.
        server = ctx.message.server
        if server.id not in self.settings["SERVERS"]:
            self.settings["SERVERS"][server.id] = False
        else:
            self.settings["SERVERS"][server.id] = not self.settings["SERVERS"][server.id]
        #for a toggle, settings should save here in case bot fails to send message
        fileIO("data/alot/settings.json", "save", self.settings)
        if self.settings["SERVERS"][server.id]:
            await self.bot.say("The alots are here! \o/")
        else:
            await self.bot.say("I'll miss you alot :cry:")

    async def alot_of_checks(self, message):
        if message.author.id == self.bot.user.id:
            return

        server = message.server
        #let PMs
        if server != None:
            if server.id not in self.settings["SERVERS"]:
                #default off
                self.settings["SERVERS"][server.id] = False
            if not self.settings["SERVERS"][server.id]:
                return


        lower = message.content.lower()
        if ' ' not in lower:
            return

        if lower == "what's an alot?":
            await self.bot.send_message(message.channel, "This is an alot: http://hyperboleandahalf.blogspot.com/2010/04/alot-is-better-than-you-at-everything.html")
            return

        lowerm = re.sub(self.alotRegex,"",lower,1)
        if lowerm == lower:
            return


        matchedKeys = re.findall(self.keyRegex,lowerm)
        matchedTags = []
        print(matchedKeys)
        for k in matchedKeys:
            vals = self.alotTags[k]
            for tag in vals:
                if tag not in matchedTags:
                    matchedTags.append(tag)
        url = ""
        if matchedTags == []:
            url = randchoice(list(self.alots.values()))
        else:
            url = self.alots[randchoice(matchedTags)]
        await self.bot.send_message(message.channel,url)


class AlotsMissing(Exception):
    pass

def check_folders():
    if not os.path.exists("data/alot"):
        print("Creating data/alot folder...")
        os.makedirs(folder)

def check_files():
    default = {"SERVERS" : {}}
    if not os.path.isfile("data/alot/settings.json"):
        print("Creating default alot settings.json...")
        fileIO("data/alot/settings.json", "save", default)

    if not os.path.isfile("data/alot/alots.json"):
        raise AlotsMissing('alots.json is missing. [p]cog update this cog')

def setup(bot):
    check_folders()
    check_files()
    n = Alot(bot)
    bot.add_listener(n.alot_of_checks, "on_message")
    bot.add_cog(n)
