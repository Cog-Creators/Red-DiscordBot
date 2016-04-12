import discord
import datetime
from discord.ext import commands
import aiohttp
import asyncio
import json
from .utils.dataIO import fileIO
import os

class rev:

    """ReversedOblivion's Custom Commands\nSome commands are finicky!"""
    def __init__(self, bot):
        self.bot = bot
        self.settings = fileIO("data/rev/config.json", "load")

    @commands.command(pass_context=True, no_pm=True)
    async def time(self):
        """Display your local date and time."""
        now = datetime.datetime.now()
        await self.bot.say('`The date is %s/%s/%s, and the time is %s:%s:%s.`' % (now.month, now.day, now.year, now.hour, now.minute, now.second))

    @commands.command(pass_context=True, no_pm=True)
    async def iloveyou(self, ctx):
        """Confess your love for the bot."""
        author = ctx.message.author
        await self.bot.send_message(ctx.message.channel, 'I love you too, {}. :heart:'.format(author.mention))

    @commands.command(pass_context=True)
    async def goodnight(self, ctx):
        """Says goodnight to someone in a PM."""
        sleeper = ctx.message.author
        await self.bot.whisper("`Hope you have a good night's rest, {}!`".format(sleeper))

    @commands.command(pass_context=True) #You can also use the "server" command, but that one prints out other info as well.
    async def serverid(self, ctx):
        """Prints out the server ID."""
        server_id = ctx.message.server
        await self.bot.say("The server ID is: `" + server_id.id + "`")

def check_folders():
    folders = ("data", "data/rev/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def check_files():
    roles = {"approvedroles" : ["Admin", "Mod"], "deniedroles" : ["Muted"]}

    if not os.path.isfile("data/rev/config.json"):
        print("Creating default config.json...")
        fileIO("data/rev/config.json", "save", roles)
        print()

def setup(bot):
    check_folders()
    check_files()
    n = rev(bot)
    bot.add_cog(n)
