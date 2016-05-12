import discord
from discord.ext import commands
import time
from __main__ import send_cmd_help


class Ping:
    """a semi-actual ping"""

    def __init__(self,bot):
        self.bot = bot
        

    @commands.command(pass_context=True)
    async def pingt(self,ctx):
        """psuedo-ping time"""
        channel = ctx.message.channel
        t1 = time.perf_counter()
        await self.bot.send_typing(channel)
        t2 = time.perf_counter()
        await self.bot.say("psuedo-ping: {}ms".format(round((t2-t1)*1000)))


def setup(bot):
    bot.add_cog(Ping(bot))


