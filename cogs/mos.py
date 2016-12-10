import discord
from discord.ext import commands
from .utils.chat_formatting import *
from random import randint
from random import choice as randchoice
import datetime
import time
import aiohttp
import asyncio
import csv
import shelve




class mos:
    """ Made of Styrofoam Specific Commands."""
    d = shelve.open('myfile.db')
    FUCKS = d['fucks']
    d.close() 


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

        mos.FUCKS['quix'] += 1
        f = mos.FUCKS['quix']
        await self.bot.say(f)

        fucks = {'quix': f}
        d = shelve.open('myfile.db')
        d['fucks'] = fucks
        d.close()    
    @commands.command(hidden=True)
    async def bmi(self):
        nbmi = randint(1,37)
        await self.bot.say("your \" BMI \" is {}. \nAlgorithm provided by Quixoticelixer".format(nbmi))
        
def setup(bot):
    n = mos(bot)
    bot.add_cog(n)
