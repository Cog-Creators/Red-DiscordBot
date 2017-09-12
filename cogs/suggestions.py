import discord
import os
import re
from discord.ext import commands
from .utils.dataIO import dataIO 
from .utils import checks

class Suggestions:
    """Posts backlog suggestions to #backlog"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/suggestions/suggestions.json"
        self.suggestions = dataIO.load_json(self.file_path)

    @commands.command(aliases=["s", "new"], pass_context=True)
    async def suggestion(self, ctx, *, text):
        """Add a suggestion from any user"""

        # The structure should be:
        #   { User : { timestamp : { BACKLOG_STATE : suggestion_string } } }
        #   { BACKLOG_STATE : { User : { timestamp : Suggestion_string } } } <-- probably better?

        user = str(ctx.message.author)
        suggestion_string = ctx.message.content
        if user not in self.suggestions:
            self.suggestions[user] = {}
        index = len(self.suggestions[user])+1
        if index > 10:
            await self.bot.say("You already have 10 suggestions!")
            return
        self.suggestions[user][str(index)] = text
        dataIO.save_json(self.file_path, self.suggestions)
        await self.bot.say("Thank you for your contribution.")

    @commands.command()
    @checks.mod_or_permissions(manage_server=True)
    async def backlog(self):
        """Pretty-print the backlog"""
        
        backlog= "```md\n"
        for author in self.suggestions:
            backlog+="# "+re.sub(r'\#\d{4}','',author)+"\n"
            for entry in self.suggestions[author]:
                backlog+="* "+self.suggestions[author][entry]+"\n" 
            backlog+="\n"
        backlog+= "```"
        await self.bot.say(backlog)

def check_folder():
    if not os.path.exists("data/suggestions"):
        print("Creating data/suggestions folder...")
        os.makedirs("data/suggestions")

def check_file():
    suggestions = {}

    f = "data/alias/suggestions.json"
    if not os.path.isfile(f):
        print("Creating default suggestions.json...")
        dataIO.save_json(f, suggestions)

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Suggestions(bot))

