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

r = redis.StrictRedis(host='localhost', port=6379, db=0)

class mos:
    """ Made of Styrofoam Specific Commands."""
    FUCKS = int(r.get('Quixoticelixer'))

    def __init__(self,bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def noot(self):
        "NOOT"
        await self.bot.say("NOOT")

    @commands.command(hidden=True)
    async def fuckquix(self):
        "fuckquix lol"
        d = shelve.open('myfile.db')

        mos.FUCKS += 1
        f = mos.FUCKS
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
            await self.bot.say("https://github.com/Quixoticelixer/Red-DiscordBot/blob/develop/data/images/feshtank.JPG?raw=true")
        elif num == 3:
            await self.bot.say("https://github.com/Quixoticelixer/Red-DiscordBot/blob/develop/data/images/feshtank2.JPG?raw=true")
        elif num == 4:
            await self.bot.say("https://github.com/Quixoticelixer/Red-DiscordBot/blob/develop/data/images/subaru1.JPG?raw=true")
    @commands.command()
    async def miata(self):
        await self.bot.say(":rainbow:")
        


def setup(bot):
    n = mos(bot)
    bot.add_cog(n)
