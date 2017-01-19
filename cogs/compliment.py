import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from random import choice as randchoice
import os


class Compliments:

    """MARViN's Compliments Cog"""
    def __init__(self, bot):
        self.bot = bot
        self.compliments = fileIO("data/compliment/compliments.json","load")

    @commands.command(pass_context=True, no_pm=True)
    async def compliment(self, ctx, user : discord.Member=None):
        """Compliments a user"""

        msg = ' '
        if user != None:
            if user.id == self.bot.user.id:
                user = ctx.message.author
                msg = " You is Kind, You is Smart, You is Important! Thank you for thinking about me!"
                await self.bot.say(user.mention + msg)
            else:
                await self.bot.say(user.mention + msg + randchoice(self.compliments))
        else:
            await self.bot.say(ctx.message.author.mention + msg + randchoice(self.compliments))


def check_folders():
    folders = ("data", "data/compliment/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    """Moves the cog to the data directory. Important -> Also changes the name to compliments.json"""
    compliments = {"You are now a very important person in my existence! Remember to spread the thing they call love around!"}

    if not os.path.isfile("data/compliment/compliments.json"):
        if os.path.isfile("cogs/put_in_cogs_folder.json"):
            print("moving default compliments.json...")
            os.rename("cogs/put_in_cogs_folder.json", "data/compliment/compliments.json")
        else:
            print("creating default compliments.json...")
            fileIO("data/compliment/compliments.json", "save", compliments)


def setup(bot):
    check_folders()
    check_files()
    n = Compliments(bot)
    bot.add_cog(n)
