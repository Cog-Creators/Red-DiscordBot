import discord
from discord.ext import commands
from random import choice as rndchoice
from .utils.dataIO import fileIO
from .utils import checks
import os

defaults = [
    "Twentysix's Floppy Disk",
    "Eslyium's Hentai Collection",
    "A Nuke",
    "A Loaf Of Bread",
    "My Hand",
    "Will's SquidBot",
    "JennJenn's Penguin Army",
    "Red's Transistor",
    "Asu\u10e6's Wrath",
    "Skordy's Keyboard"]

class Slap:
    """Slap command."""

    def __init__(self, bot):
        self.bot = bot
        self.items = fileIO("data/slap/items.json", "load")

    def save_items(self):
        fileIO("data/slap/items.json", 'save', self.items)

    @commands.group(pass_context=True, invoke_without_command=True)
    async def slap(self, ctx, *, user : discord.Member=None):
        """Slap a user"""
        if ctx.invoked_subcommand is None:
            if user.id == self.bot.user.id:
                user = ctx.message.author
                await self.bot.say("Dont make me slap you instead " + user.name)
                return
            await self.bot.say("-slaps " + user.name + " with " +
                               (rndchoice(self.items) + "-"))

    @slap.command()
    async def add(self, item):
        """Adds an item"""
        if item in self.items:
          await self.bot.say("That is already an item.")
        else:
          self.items.append(item)
          self.save_items()
          await self.bot.say("Item added.")

    @slap.command()
    @checks.is_owner()
    async def remove(self, item):
        """Removes item"""
        if item not in self.items:
          await self.bot.say("That is not an item")
        else:
            self.items.remove(item)
            self.save_items()
            await self.bot.say("item removed.")

def check_folders():
    if not os.path.exists("data/slap"):
        print("Creating data/slap folder...")
        os.makedirs("data/slap")

def check_files():
    f = "data/slap/items.json"
    if not fileIO(f, "check"):
        print("Creating empty items.json...")
        fileIO(f, "save", defaults)

def setup(bot):
    check_folders()
    check_files()
    n = Slap(bot)
    bot.add_cog(n)
