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
        nbmi = random.uniform(2,39)
        await self.bot.say("your \" BMI \" is {:3.2f}. \nAlgorithm provided by Quixoticelixer".format(nbmi))
        
    @commands.command(hidden=True)
    async def addme(self, days, name):
        r.zadd('daysSince', days, name) 
        await self.bot.say('added {}'.format(name))

    @commands.command(hidden=True)
    async def days_since(self, name):
        days = r.zscore('daysSince', name)
        await self.bot.say(days)

def setup(bot):
    n = mos(bot)
    bot.add_cog(n)
