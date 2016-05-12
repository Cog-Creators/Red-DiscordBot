import discord
from discord.ext import commands
from cogs.utils.dataIO import fileIO
from cogs.utils import checks
from __main__ import send_cmd_help
import os
from random import choice as randchoice

class Quotes:
    def __init__(self,bot):
        self.bot = bot
        self.quotes = fileIO("data/quotes/quotes.json","load")

    def _get_random_quote(self):
        if len(self.quotes) == 0:
            send_cmd_help(self.quote)
            return "There are no saved quotes!"
        return randchoice(self.quotes)

    def _get_quote(self,num):
        if num > 0 and num <= len(self.quotes):
            return self.quotes[num-1]
        else:
            return "That quote doesn't exist!"

    def _add_quote(self,message):
        self.quotes.append(message)
        fileIO("data/quotes/quotes.json","save",self.quotes)

    def _fmt_quotes(self):
        ret = "```"
        for num,quote in enumerate(self.quotes):
            ret += str(num+1) + ") "+quote+"\n"
        ret += "```"
        return ret

    @commands.command()
    async def delquote(self, num : int):
        """Deletes a quote by its number

           Use !allquotes to find quote numbers
           Example: !delquote 3"""
        if num > 0 and num <= len(self.quotes):
            quotes = []
            for i in range(len(self.quotes)):
                if num-1 == i:
                    await self.bot.say("Quote number "+str(num)+" has been deleted.")
                else:
                    quotes.append(self.quotes[i])
            self.quotes = quotes
            fileIO("data/quotes/quotes.json","save",self.quotes)
        else:
            await self.bot.say("Quote "+str(num)+" does not exist.")

    @commands.command(pass_context=True)
    async def allquotes(self,ctx):
        """Gets a list of all quotes"""
        strbuffer = self._fmt_quotes().split("\n")
        mess = ""
        for line in strbuffer:
            if len(mess) + len(line) + 1 < 2000:
                mess += "\n" + line
            else:
                await self.bot.send_message(ctx.message.author,mess)
                mess = ""
        if mess != "":
            await self.bot.send_message(ctx.message.author,mess)

    @commands.command()
    async def quote(self,*message):
        """Adds quote, retrieves random one, or a numbered one.
               Use !allquotes to get a list of all quotes.

           Example: !quote The quick brown fox -> adds quote
                    !quote -> gets random quote
                    !quote 4 -> gets quote #4"""
        try:
            if len(message) == 1:
                message = int(message[0])
                await self.bot.say(self._get_quote(message))
                return
        except:
            pass
        message = " ".join(message)
        if message.lstrip() == "":
            await self.bot.say(self._get_random_quote())
        else:
            self._add_quote(message)
            await self.bot.say("Quote added.")

def check_folder():
    if not os.path.exists("data/quotes"):
        print("Creating data/quotes folder...")
        os.makedirs("data/quotes")

def check_file():
    quotes = []

    f = "data/quotes/quotes.json"
    if not fileIO(f, "check"):
        print("Creating default quotes's quotes.json...")
        fileIO(f, "save", quotes)

def setup(bot):
    check_folder()
    check_file()
    n = Quotes(bot)
    bot.add_cog(n)