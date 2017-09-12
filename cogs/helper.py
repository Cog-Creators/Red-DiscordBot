import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from .utils import checks
from enum import Enum
from __main__ import send_cmd_help

class Helper:
    """Contains most static-based commands"""

    def __init__(self, bot, resources_folder):
        self.privilege = dataIO.load_json(
            resources_folder+"/character_privilege.json")
        self.bot = bot

    @commands.command()
    async def yup(self):
        """Documentation""" #TODO
        await self.bot.say("yup")

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def smash(self, ctx):
        """Changes smash module settings"""
        await send_cmd_help(ctx)


def check_folders():
    if not os.path.exists("data/resources"):
        print("Creating data/resources folder...")
        os.makedirs("data/resources")

def check_files():
    f = "data/resources/character_privilege.json"
    if not fileIO(f, "check"):
        print("Creating empty character_privilege.json...")
        fileIO(f, "save", [])

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Helper(bot, "data/resources"))
