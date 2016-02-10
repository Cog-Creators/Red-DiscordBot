import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import os

class Quote:
    """Quotes"""

    def __init__(self, bot):
        self.bot = bot
        self.q_quote = fileIO("data/quote/quote.json", "load")

    @commands.command(pass_context=True, no_pm=True)
    async def addquote(self, ctx, quote : str, *text):
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
        if quote not in quotelist:
            quotelist[quote] = text
            print(quotelist[quote])
            self.q_quote[server.id] = quotelist
            print(self.q_quote)
            fileIO("data/quote/quote.json", "save", self.q_quote)
            await self.bot.say("`Quote added.`")
        else:
            await self.bot.say("`Quote already exists.`")

    async def checkQ(self, message):
        if message.author.id == self.bot.user.id or len(message.content) < 2 or message.channel.is_private:
            return
        msg = message.content
        server = message.server
        if msg[0] in self.bot.command_prefix and server.id in self.q_quote.keys():
            quotelist = self.q_quote[server.id]
            if msg[1:] in quotelist:
                await self.bot.send_message(message.channel, quotelist[msg[1:]])

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
    bot.add_listener(n.checkQ, "on_message")
    bot.add_cog(n)
