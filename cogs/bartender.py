from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
# Sys.
from operator import itemgetter, attrgetter
import discord
from discord.ext import commands
#from copy import deepcopy
#import aiohttp
#import asyncio
import json
import os
import time


try:
    from PIL import Image, ImageDraw, ImageFont
    pil_available = True
except:
    pil_available = False
try:
    import emoji
    emoji_available = False
except:
    emoji_available = True


DIR_DATA = "data/bartender"
SETTINGS = DIR_DATA+"/settings.json"
BACKUP = DIR_DATA+"/bank_backup.json"
BANK = "data/economy/bank.json"

class Bartender:
    """Buy a drink at the bar"""
    def __init__(self,bot):
        self.bot = bot
        self.settings = fileIO(SETTINGS, "load")
        self.items = [["beer", ":beer:", 2], ["wine", ":wine_glass:", 2], ["cocktail", ":cocktail:", 4], ["tropical", ":tropical_drink:", 5], ["sake", ":sake:", 4], ["champagne", ":champagne:", 30], ["tea", ":tea:", 1], ["coffee", ":coffee:", 1]]
        self.numbers = ["one", "two", "tree", "four", "five", "six", "seven", "eight", "nine", "ten"]
        
    @commands.command(pass_context=True, no_pm=False)
    async def buy(self, ctx, amount : int, drink):
        """Buy a drink"""
        botuser = self.bot.user
        content = ctx.message.content      
        mentions = ctx.message.mentions       
        author = ctx.message.author
        
        #Get Economy data
        if self.econ_interlink() != None:
            econ = self.econ_interlink()
        else:
            await self.bot.say("[#1] We are closed atm.")
            return
        
        price = -1
        icon = ""
        available = False
        for i, item in enumerate(self.items):
            #print(i)
            #print(item)
            if drink == self.items[i][0]:
                icon = self.items[i][1]
                price = self.items[i][2]*amount
                available = True
                break
        if not available:
            await self.bot.say("Im sorry to dissapoint you, we dont serve {}".format(drink))
            return

        buy_for = []
        for member in mentions:
            buy_for.append(member.mention)
        buy_for = " ".join(buy_for)

        
        if econ.enough_money(author.id, price):
            econ.withdraw_money(author.id, price)
            econ.add_money(botuser.id, price)
             
            drinks = ""
            for d in range(0,amount):
                drinks = drinks+icon
            if buy_for == "":
                msg = "{} There you go mate {}".format(buy_for, drinks)
                msg = emoji.emojize(msg, use_aliases=True)
                await self.bot.say(msg)
            else:
                if amount > 1:
                    msg = "{0} Have some {1}'s from {2}{3}".format(buy_for, drink, author, drinks)
                    msg = emoji.emojize(msg, use_aliases=True)
                    await self.bot.say(msg)
                else:
                    msg ="{0} Have some {1} from {2}{3}".format(buy_for, drink, author, drinks)
                    msg = emoji.emojize(msg, use_aliases=True)
                    await self.bot.say(msg)
        else:
            try:
                text_num = self.numbers[amount-1]
            except Exception as e:
                text_num = str(amount)
            await self.bot.say("{0} Sorry mate, you don't have enough money for {1} {2}.\n it cost's {3}".format(author.mention, text_num, drink, price))

    @commands.command(pass_context=True, no_pm=False)
    async def beverages(self, ctx):
        author = ctx.message.author  
        msg = "**We have: **"
        for b in self.items:
            msg = msg + "{} ${}, ".format(b[0], b[2])
        await self.bot.say(msg)
        
    #if Economy.py updates, this may break
    @commands.command(pass_context=True)
    @checks.is_owner()
    async def registerbar(self, ctx, agree : str):
        """Opens the bar and registers the bot into Economy.py bank. 
        WARNING: Edits Economy.py's bank.json file.
        If Economy.py is updated in the future with a different format for bank.json, the data in bank.json (everyone's balances) may be lost.
        This command will try to save a backup in data/economytrickle/bank-backup.json in case that happens.
        If you understand this and still want to register your bot in the bank, do: [p]registerbar yes
        """
        if agree.lower() == "yes":
            econ = self.bot.get_cog('Economy')
            bank = econ.bank
            botuser = self.bot.user
            if botuser.id not in bank:
                fileIO(BACKUP, "save", bank)
                bank[botuser.id] = {"name" : botuser.name, "balance" : 100}
                fileIO("data/economy/bank.json", "save", bank)
                await self.bot.say("Account opened for {}. Current balance: {}".format(botuser.mention, str(bank[botuser.id]["balance"])))             
            else:
                await self.bot.say("{} already has an account at the Twentysix bank.".format(botuser.mention))
            fileIO(SETTINGS, "save", self.settings)
        else:
            await send_cmd_help(ctx)
            
    @commands.command(pass_context=True)
    @checks.is_owner()
    async def openbar(self, ctx):
        """Opens the bar"""
        author = ctx.message.author
        self.settings["bar_startus"] = True
        fileIO(SETTINGS, "save", self.settings)
        await self.bot.say("{} The bar is now open!.".format(author.mention)) 
        
    @commands.command(pass_context=True)
    @checks.is_owner()
    async def closebar(self, ctx):
        """Closes the bar"""
        author = ctx.message.author
        self.settings["bar_startus"] = False
        fileIO(SETTINGS, "save", self.settings)
        await self.bot.say("{} The bar is now closed!.".format(author.mention)) 

    def econ_interlink(self):
        econ = None
        econ = self.bot.get_cog('Economy')
        if econ == None:
            print("--- Error: Was not able to load Economy cog into Economytrickle. ---")
            return False
        else:
            return econ
        
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Set-up
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_folders():
    if not os.path.exists(DIR_DATA):
        print("Creating data/bartender folder...")
        os.makedirs(DIR_DATA)

def check_files():
    settings = {"bar_status" : False}
    
    if not fileIO(SETTINGS, "check"):
        print("Creating settings.json")
        fileIO(SETTINGS, "save", settings)

def setup(bot):
    if not pil_available:
        raise RuntimeError("You don't have Pillow installed, run\n```pip3 install pillow```And try again")
        return
    if not pil_available:
        raise ModuleNotFound("emoji is not installed. Do 'pip3 install emoji --upgrade' to use this cog.")
        return
    check_folders()
    check_files()
    bot.add_cog(Bartender(bot))


