import discord
from .utils import checks
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from __main__ import send_cmd_help
import os
import asyncio

class BotStats:
    "You can display your bot stats in your game status..."
    
    def __init__(self, bot):
        self.bot = bot
        self.derp = "data/botstats/json.json"
        self.imagenius = dataIO.load_json(self.derp)

    @checks.is_owner()
    @commands.group(pass_context=True)
    async def botstats(self, ctx):
        """Display Bot Stats in game status that update every 10 seconds!"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
    
    @checks.is_owner()
    @botstats.command(pass_context=True)
    async def toggle(self, ctx):
        """Turn BotStatus on and off, like a boss"""
        
        servers = str(len(self.bot.servers))
        users = str(len(set(self.bot.get_all_members())))
        if self.imagenius["TOGGLE"] is False:
            self.imagenius["TOGGLE"] = True
            self.imagenius["MAINPREFIX"] = ctx.prefix
            dataIO.save_json(self.derp, self.imagenius)
            prefix = self.imagenius["MAINPREFIX"]
            await self.bot.say("The botstats have been turned on!")
            await self.botstatz()
        else:
            self.imagenius["TOGGLE"] = False
            prefix = self.imagenius["MAINPREFIX"]
            dataIO.save_json(self.derp, self.imagenius)
            await self.bot.say("The botstats have been turned off!")
            await self.botstatz()

    @checks.is_owner()
    @botstats.command(pass_context=True)
    async def message(self, ctx, *, message):
        """You can set the way your botstats is set!


        {0} = Bot's Prefix
        {1} = Servers
        {2} = Total Users

        Default Message: {0}help | {1} servers | {2} users
        """

        prefix = self.imagenius["MAINPREFIX"]
        if self.imagenius["TOGGLE"] is True:
            await self.bot.say("Before you change the message, turn off your bot! `{}botstats toggle`".format(prefix))
        else:
            self.imagenius["MESSAGE"] = message
            dataIO.save_json(self.derp, self.imagenius)
            await self.bot.say("Congrats, you have set your message to ```{}```".format(message))


    @checks.is_owner()
    @botstats.command(pass_context=True)
    async def timeout(self, ctx, seconds : int):
        """Decide how often the BotStatus


        Default is 15
        """

        if seconds >= 15:
            self.imagenius["SECONDS2LIVE"] = seconds
            dataIO.save_json(self.derp, self.imagenius)
            await self.bot.say("Your bot status will now update every {} seconds! #BOSS".format(seconds))
        else:
            await self.bot.say("NO, IT CAN'T BE UNDER 15 SECONDS. THE PEOPLE AT DISCORD WILL FREAK....")

    async def botstatz(self):    
        while True:
            if self.imagenius["TOGGLE"] is True:
                status = self.get_status()
                servers = str(len(self.bot.servers))
                users = str(len(set(self.bot.get_all_members())))
                botstatus = self.imagenius["MESSAGE"]
                prefix = self.imagenius["MAINPREFIX"]
                message = botstatus.format(prefix, servers, users)
                game = discord.Game(name=message)
                await self.bot.change_presence(game=game, status=status)
                await asyncio.sleep(self.imagenius["SECONDS2LIVE"])
            else:
                await self.bot.change_presence(status=None, game=None)
                return
        else:
            pass
    
    async def on_ready(self):
        if self.imagenius["TOGGLE"] is True:
            while True:
                status = self.get_status()
                servers = str(len(self.bot.servers))
                users = str(len(set(self.bot.get_all_members())))
                botstatus = self.imagenius["MESSAGE"]
                prefix = self.imagenius["MAINPREFIX"]
                message = botstatus.format(prefix, servers, users)
                game = discord.Game(name=message)
                await self.bot.change_presence(game=game, status=status)
                await asyncio.sleep(self.imagenius["SECONDS2LIVE"])
            else:
                pass
        else:
            pass
    
    def get_status(self):
        typesofstatus = {
            "idle" : discord.Status.idle,
            "dnd" : discord.Status.dnd,
            "online" : discord.Status.online, 
            "invisible" : discord.Status.invisible
        }
        for server in self.bot.servers:
            member = server.me
            break
        status = member.status
        status = typesofstatus.get(str(status))
        return status
        


def check_folders():
    if not os.path.exists("data/botstats"):
        print("Creating the botstats folder, so be patient...")
        os.makedirs("data/botstats")
        print("Finish!")

def check_files():
    twentysix = "data/botstats/json.json"
    json = {
        "MAINPREFIX" : "This can be set when starting botstats thru [p]botstats toggle",
        "TOGGLE" : False,
        "SECONDS2LIVE" : 15,
        "MESSAGE" : "{0}help | {1} servers | {2} users"
    }

    if not dataIO.is_valid_json(twentysix):
        print("Derp Derp Derp...")
        dataIO.save_json(twentysix, json)
        print("Created json.json!")

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(BotStats(bot))
