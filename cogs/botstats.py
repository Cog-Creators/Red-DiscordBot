from .utils import checks
from discord.ext import commands
import discord
import os
import asyncio

class BotStats:
    "You can display your bot stats in your game status"
    
    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.command(pass_context=True)
    async def botstats(self, ctx):
        """Display Bot Stats in game status that update every 10 seconds!"""
        
        while True:
            user = ctx.message.author
            name = self.bot.user.name
            prefix = ctx.prefix
            servers = str(len(self.bot.servers))
            users = str(len(set(self.bot.get_all_members())))
            message = '{}help | {} servers | {} users'.format(prefix, servers, users)
            status = list(self.bot.servers)[0].me.status
            game = discord.Game(name=message)
            await self.bot.change_presence(status=status, game=game)
            await asyncio.sleep(10)
        else:
            pass

def setup(bot):
    bot.add_cog(BotStats(bot))
