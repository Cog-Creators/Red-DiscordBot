import discord
from .utils.dataIO import fileIO
from discord.ext import commands
from random import randint
import asyncio
import os
import ast

class Prefixes:
    """server-wide bot-prefix info"""

    def __init__(self, bot):
        self.bot = bot
        self.short_term_prefixes = {"PREFIXES":self.bot.command_prefix}
        self.allprefixes = fileIO("data/prefixes/prefixes.json", "load")
        self.prefixing = False


    #todo store who got prefixes from. who has what?

    @commands.command(pass_context=True, name="prefixes")
    async def _prefixes(self, ctx):
        """lists all the prefixes that have ever been used by any the bots in the server (so long as they had this cog)"""
        self.short_term_prefixes["PREFIXES"] = self.bot.command_prefix
        if not await self.start_prefixing(ctx):
            return
        msgs = ["List of all prefixes ever of bots with this module: \n"]
        
        m = 0
        maxm = 1980
        if self.short_term_prefixes["PREFIXES"]:
            for i, d in enumerate(self.short_term_prefixes["PREFIXES"]):
                if len(d) < maxm: #how did you get a filename this large?
                    if len(msgs[m]) + len(d) > maxm:
                        m += 1
                        msgs.append('')
                    msgs[m] += str(i)+": " + d + "\n"
            for msg in msgs:
                await self.bot.send_message(ctx.message.channel, msg)
                await asyncio.sleep(1)
        else:
            await self.bot.say("Um.. there are no prefixes?")

    @commands.command(pass_context=True)
    async def allprefixes(self, ctx):
        """lists all the prefixes that have ever been used by any the bots in the server (so long as they had this cog)"""
        if not await self.start_prefixing(ctx):
            return
        msgs = ["List of all prefixes ever of bots with this module: \n"]
        
        m = 0
        maxm = 1980
        if self.allprefixes["PREFIXES"]:
            for i, d in enumerate(self.allprefixes["PREFIXES"]):
                if len(d) < maxm: #how did you get a filename this large?
                    if len(msgs[m]) + len(d) > maxm:
                        m += 1
                        msgs.append('')
                    msgs[m] += str(i)+": " + d + "\n"
            for msg in msgs:
                await self.bot.send_message(ctx.message.channel, msg)
                await asyncio.sleep(1)
        else:
            await self.bot.say("Um.. there are no prefixes?")

        msgs = ["Bots that participated: \n"]

        if self.allprefixes["BOTS"]:
            for i, d in enumerate(self.allprefixes["BOTS"]):
                bname = ctx.message.server.get_member(d)
                if bname is None:
                    bname = "Bot left: " + d
                if len(bname) < maxm: #how did you get a filename this large?
                    if len(msgs[m]) + len(bname) > maxm:
                        m += 1
                        msgs.append('')
                    msgs[m] += str(i)+": " + bname + "\n"
            for msg in msgs:
                await self.bot.send_message(ctx.message.channel, msg)
                await asyncio.sleep(1)
        else:
            await self.bot.say("No bots participated")

    @commands.command(pass_context=True)
    async def available(self, ctx, *prefix):
        """communicates with other bots to see if a prefix is available"""
        self.short_term_prefixes["PREFIXES"] = self.bot.command_prefix
        if not await self.start_prefixing(ctx):
            return
        for p in prefix:
            if p not in self.short_term_prefixes["PREFIXES"]:
                await self.bot.say(p + " is available")
            else:
                await self.bot.say(p + " is taken")
            await asyncio.sleep(1)
    
    @commands.command(pass_context=True)
    async def participate(self,ctx):
        """to participate, just grab the cog here: https://github.com/RedDiscordDocs/ServerPrefixTracking"""
        await self.bot.say('If you would like your bot to participate, please grab prefixes.py from here and put it into your cogs folder. https://github.com/RedDiscordDocs/ServerPrefixTracking')


    async def start_prefixing(self, ctx):
        await asyncio.sleep(randint(0,5))
        if self.prefixing:
            return False
        await self.bot.send_message(ctx.message.channel,'`|\u200bprefixing\u200b|`')
        await asyncio.sleep(8)
        return True

    async def on_message(self,message):
        if message.author.id == self.bot.user.id:
            return
        if message.content == '`|\u200bprefixing\u200b|`':
            self.prefixing = True
            msg = await self.bot.send_message(message.channel,'`|\u200bme\u200b|`')
            await asyncio.sleep(1)
            await self.bot.delete_message(msg)
            await asyncio.sleep(7)
            self.prefixing = False
        elif message.content == '`|\u200bme\u200b|`':
            await self.bot.send_message(message.author,'|\u200bmy prefixes <3\u200b|'+str(self.bot.command_prefix))
        elif message.content.startswith('|\u200bmy prefixes <3\u200b|'):
            pstring = message.content.replace('|\u200bmy prefixes <3\u200b|','')
            botpref = ast.literal_eval(pstring)
            if message.author.id not in self.allprefixes["BOTS"]:
                self.allprefixes["BOTS"].append(message.author.id)
            self.short_term_prefixes["PREFIXES"] = list(set(botpref) | set(self.short_term_prefixes["PREFIXES"]))
            self.allprefixes["PREFIXES"] = list(set(self.short_term_prefixes["PREFIXES"]) | set(self.allprefixes["PREFIXES"]))
            fileIO('data/prefixes/prefixes.json', "save", self.allprefixes)


def check_folders():
    if not os.path.exists('data/prefixes'):
        print("Creating data/prefixes folder...")
        os.makedirs('data/prefixes')

def check_files(bot):
    if not os.path.isfile('prefixes/prefixes.json'):
        print("Creating default prefixes settings.json...")
        fileIO('data/prefixes/prefixes.json', "save", {"PREFIXES":bot.command_prefix, "BOTS":[]})
    else:
        current = fileIO('data/prefixes/prefixes.json', "load")
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print("Adding " + str(key) + " field to prefixes prefixes.json")

def setup(bot):
    check_folders()
    check_files(bot)
    bot.add_cog(Prefixes(bot))
