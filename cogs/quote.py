import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from datetime import date
import os

class Quote:
    """Quotes"""

    def __init__(self, bot):
        self.bot = bot
        self.q_quote = fileIO("data/quote/quote.json", "load")

    @commands.command(pass_context=True, no_pm=True)
    async def addquote(self, ctx : str, *text):
        """Adds a quote to the database

        Example:
        !addquote Enter quote text here
        """
        if text == ():
            await self.bot.say("addquote [quote text]")
            return
        server = ctx.message.server
        channel = ctx.message.channel
        text = " ".join(text)
        if not server.id in self.q_quote:
            self.q_quote[server.id] = {}
        quotelist = self.q_quote[server.id]
        if text not in quotelist:
            d = date.today()
            quotelist[text] = d.strftime("%d/%m/%Y")
            self.q_quote[server.id] = quotelist
            fileIO("data/quote/quote.json", "save", self.q_quote)
            await self.bot.say("`Quote added.`")
        else:
            await self.bot.say("`Quote already exists.`")



def check_folders():
    if not os.path.exists("data/quote"):
        print("Creating data/quote folder...")
        os.makedirs("data/quote")

def check_files():
    f = "data/quote/quote.json"
    if not fileIO(f, "check"):
        print("Creating empty quote.json...")
        fileIO(f, "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = Quote(bot)
    bot.add_cog(n)
