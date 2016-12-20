import discord
from discord.ext import commands
from .utils.chat_formatting import *
from random import randint
from random import choice as randchoice
import random
import datetime
import time
import aiohttp
import asyncio
import csv
import redis
import datetime
from datetime import date
from datetime import timedelta
import time
import math
import pint
from currency_converter import CurrencyConverter

c = CurrencyConverter()
ureg = pint.UnitRegistry()
r = redis.StrictRedis(host='localhost', port=6379, db=0)

class mos:
    """ Made of Styrofoam Specific Commands."""
    awd,AWD = 3,3
    rwd,RWD = 2,2
    fwd,FWD = 1,1

    def __init__(self,bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def noot(self):
        "NOOT"
        await self.bot.say("NOOT")

    @commands.command(hidden=True)
    async def fuckquix(self):
        "fuckquix lol"
        FUCKS = int(r.get('Quixoticelixer'))
        FUCKS += 1
        f = FUCKS
        await self.bot.say(f)
        r.set('Quixoticelixer',f)

    @commands.command(hidden=True)
    async def bmi(self):
        nbmi = random.normalvariate(18,8)
        await self.bot.say("your \" BMI \" is {:3.2f}. \nAlgorithm provided by Quixoticelixer".format(nbmi))


    @commands.command()
    async def fesh(self):
        "random fesh emoji"
        num = random.randint(1,5)

        if num == 1:
            await self.bot.say("https://github.com/Quixoticelixer/Red-DiscordBot/blob/develop/data/images/nigel.JPG?raw=true")
        elif num == 2:
            await self.bot.say("https://github.com/Quixoticelixer/Red-DiscordBot/blob/develop/data/images/feshtank.jpg?raw=true")
        elif num == 3:
            await self.bot.say("https://github.com/Quixoticelixer/Red-DiscordBot/blob/develop/data/images/feshtank2.JPG?raw=true")
        elif num == 4:
            await self.bot.say("https://github.com/Quixoticelixer/Red-DiscordBot/blob/develop/data/images/subaru1.JPG?raw=true")
    @commands.command()
    async def miata(self):
        await self.bot.say("https://goo.gl/s9MKcU :rainbow::gay_pride_flag::rainbow::rainbow::gay_pride_flag::rainbow::rainbow::rainbow::rainbow::rainbow::rainbow::rainbow::rainbow:::gay_pride_flag::rainbow:::gay_pride_flag::rainbow:::gay_pride_flag::rainbow:::gay_pride_flag::rainbow::gay_pride_flag:")

    @commands.command()
    async def ginger(self):
        await self.bot.say("http://www.ranga.co.nz/wp-content/uploads/2015/12/Ranga-GB-6Pack.jpg")

    @commands.command()
    async def calc(self, input):
       try:
           await self.bot.say(eval(input))
       except ZeroDivisionError:
           weighted_choices = [('noot', 1),('0', 28), ('1', 28), ('git', 1), ('max', 1),('f', 2),('x', 2),('iqx',1),('-2', 1)]
           stringer = [val for val, cnt in weighted_choices for i in range(cnt)]
           output = 'fml'
           for x in range (0,90):
                 output = output + str(random.choice(stringer))
           await self.bot.say(output)

    @commands.command()
    async def add_poni(self, name, picture):
        r.set(name, picture)
        await self.bot.say("added {}".format(name))

    @commands.command()
    async def get_poni(self, name):
        try:
            pname = r.get(name).decode('utf-8')
            await self.bot.say(pname)
        except AttributeError:
            await self.bot.say("```That poni can not be found.```")

    @commands.command(pass_context=True)
    async def say(self,ctx, input):

        await self.bot.say(input)

        await client.delete_message("!say noot")
def setup(bot):
    n = mos(bot)
    bot.add_cog(n)
