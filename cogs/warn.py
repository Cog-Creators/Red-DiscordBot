"""Warning cog"""
import discord
import os
import shutil
import aiohttp
import asyncio
import os

from .utils.chat_formatting import *
from .utils.dataIO import fileIO, dataIO
from .utils import checks
from discord.ext import commands 
from enum import Enum
from __main__ import send_cmd_help

colour = '099999'

class Warn:
    def __init__(self, bot):
        self.bot = bot
        self.profile = "data/account/warnings.json"
        self.riceCog = dataIO.load_json(self.profile)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(kick_members=True)
    async def warn(self, ctx, user : discord.Member):
        """Warns the user - At 3 warnings the user gets kicked"""
       
        server = ctx.message.server
        author = ctx.message.author

        #checks if the user is in the file
        
        if server.id not in self.riceCog:
            self.riceCog[server.id] = {}
            dataIO.save_json(self.profile, self.riceCog)
            if user.id not in self.riceCog[server.id]:
                self.riceCog[server.id][user.id] = {}
                dataIO.save_json(self.profile, self.riceCog)
            else:
                pass
        else:
            if user.id not in self.riceCog[server.id]:
                self.riceCog[server.id][user.id] = {}
                dataIO.save_json(self.profile, self.riceCog)
            else:
                pass

        if "Count" in self.riceCog[server.id][user.id]:
            count = self.riceCog[server.id][user.id]["Count"]
        else:
            count = "0"

        #checks how many warnings the user has
        if count == "2":
            count = "0"
            self.riceCog[server.id][user.id].update({"Count" : count})
            dataIO.save_json(self.profile, self.riceCog)
            try:
                msg = str(user.name) + " has been **kicked** after 3 warnings."
                data = discord.Embed(colour=discord.Colour(value=colour))
                data.add_field(name="Warning", value=msg)
                data.set_footer(text="riceBot")
                await self.bot.say(embed=data)
                await self.bot.kick(user)
            except discord.errors.Forbidden:
                await self.bot.say("I'm not allowed to do that.")
            except Exception as e:
                print(e)


        elif count == "1":
            msg = str(user.mention) + ", you have received your second warning! One more warning and you will be **kicked**!"
            data = discord.Embed(colour=discord.Colour(value=colour))
            data.add_field(name="Warning", value=msg)
            data.set_footer(text="riceBot")
            await self.bot.say(embed=data) 
            
            count = "2"
            self.riceCog[server.id][user.id].update({"Count" : count})
            dataIO.save_json(self.profile, self.riceCog)
        else:
            msg = str(user.mention) + ", you have received your first warning! At three warnings you will be **kicked**!"
            data = discord.Embed(colour=discord.Colour(value=colour))
            data.add_field(name="Warning", value=msg)
            data.set_footer(text="riceBot")
            await self.bot.say(embed=data)
           
            count = "1"
            self.riceCog[server.id][user.id].update({"Count" : count})
            dataIO.save_json(self.profile, self.riceCog)

    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(kick_members=True)
    async def clean(self, ctx, user : discord.Member):
        author = ctx.message.author
        server = author.server

        if server.id not in self.riceCog:
            self.riceCog[server.id] = {}
            dataIO.save_json(self.profile, self.riceCog)
            if user.id not in self.riceCog[server.id]:
                self.riceCog[server.id][user.id] = {}
                dataIO.save_json(self.profile, self.riceCog)
            else:
                pass
        else:
            if user.id not in self.riceCog[server.id]:
                self.riceCog[server.id][user.id] = {}
                dataIO.save_json(self.profile, self.riceCog)
            else:
                pass

        if "Count" in self.riceCog[server.id][user.id]:
            count = self.riceCog[server.id][user.id]["Count"]
        else:
            count = "0"

        if count != 0:
            msg = str(user.mention) + ", your warnings have been cleared!"
            data = discord.Embed(colour=discord.Colour(value=colour))
            data.add_field(name="Warning", value=msg)
            data.set_footer(text="riceBot")
            await self.bot.say(embed=data) 
            
            count = "0"
            self.riceCog[server.id][user.id].update({"Count" : count})
            dataIO.save_json(self.profile, self.riceCog)
        else:
            await self.bot.say("You don;t have any warnings to clear, " + str(user.mention) + "!")





def check_folder():
    if not os.path.exists("data/account"):
        print("Creating data/account folder")
        os.makedirs("data/account")

def check_file():
    data = {}
    f = "data/account/warnings.json"
    if not dataIO.is_valid_json(f):
        print("Creating data/account/warnings.json")
        dataIO.save_json(f, data)
 
def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Warn(bot))