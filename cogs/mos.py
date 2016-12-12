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
import shelve
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
        
    @commands.command(pass_context = True)
    async def addme(self,ctx, days_slc : int):
        "Adds you to the days_since db \nAdd the initial days after the command "

        user = ctx.message.author
        d,m,y = time.strftime("%d,%m,%Y").split(",")
        d = int(d); m = int(m); y = int(y);
        t1 = date(y,m,d)
        t1 = t1 + timedelta(days = days_slc)
        date_slc = str(t1) 
        r.hset('user:{}'.format(user),'date_slc', date_slc) 

        await self.bot.say('added {}'.format(user))


    @commands.command(hidden = True,pass_context=True)
    async def days_since(self, ctx):
        "Shows the days since you last..."
        user = ctx.message.author
        
        y,m,d = str(r.hget('user:{}'.format(user), 'date_slc'), 'utf-8').split("-")
        d = int(d); m = int(m); y = int(y);
        t1 = date(y,m,d)
        d,m,y = time.strftime("%d:%m:%Y").split(":")
        d = int(d); m = int(m); y = int(y);
        t2 = date(y,m,d)
        try:
            time_delta, minutes = str(t1 - t2).split(",")
        except ValueError:
            await self.bot.say("0 Days ໒( •́ ‸ •̀ )७"" ")
        else:
            await self.bot.say("{}".format(time_delta))

    @commands.command(pass_context = True)
    async def reset(self,ctx, days_slc : int = 0):
        "Adds you to the days_since db \nAdd the initial days after the command "

        user = ctx.message.author
        d,m,y = time.strftime("%d,%m,%Y").split(",")
        d = int(d); m = int(m); y = int(y);
        t1 = date(y,m,d)
        t1 = t1 + timedelta(days = days_slc)
        date_slc = str(t1) 
        r.hset('user:{}'.format(user),'date_slc', date_slc) 

        await self.bot.say('໒( •́ ‸ •̀ )७ {} '.format(user))

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
    async def convert(self, unit1, unit2):
        unit1 = int(unit1)
        if unit2 == 'kg' or unit2 == 'kgs':
            unit3 = unit1 * ureg.kilogram
            unit3 = unit3.to(ureg.lbs)
            await self.bot.say("{}kgs is {:3.1f}s".format(unit1,unit3))
        elif unit2 == 'lb' or unit2 == 'lbs':
            unit3 = unit1 * ureg.lbs
            unit3 = unit3.to(ureg.kg)
            await self.bot.say("{}lbs is {:3.1f}s".format(unit1,unit3))
   # @commands.command()
  #  async def moni_convert(self, unit):
   #     eur = c.convert(unit, 'USD','EUR')
   #     cad = c.convert(unit, 'USD','CAD')
   #     nzd = c.convert(unit, 'USD','NZD')
   #     aud = c.convert(unit, 'USD','AUD')

        # await self.bot.say('{0} USD is {1:7.2f} EUR, {2:7.2f} CAD, {3:7.2f} NZD, {4:7.2f} AUD'.format(unit,eur,cad,nzd,aud))

def setup(bot):
    n = mos(bot)
    bot.add_cog(n)
