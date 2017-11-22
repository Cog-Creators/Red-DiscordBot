# Feature tracker cog for Red-DiscordBot by Twentysix, an
#   open-source discord bot (github.com/Cog-Creators/Red-DiscordBot)
#
# Authored by Swann (github.com/swannobi)
#
# Last updated Nov 17, 2017
#
# Currently offers basic functionality. Look to a future version
#   for a complete project management solution.

import discord
import os
import re
from discord.ext import commands
from .utils.dataIO import dataIO 
from .utils import checks
from __main__ import send_cmd_help


class Suggestions:
    """Tracks a suggestions backlog for admins/developers of a server."""

    def __init__(self, bot):
        self.bot = bot
        self.suggestions_path = "data/suggestions/suggestions.json"
        self.settings_path = "data/suggestions/settings.json"
        self.board_path = "data/suggestions/board.json"
        self.suggestions = dataIO.load_json(self.suggestions_path)
        self.settings = dataIO.load_json(self.settings_path)
        self.board = dataIO.load_json(self.board_path)

    def _get_user_from_id(self, server, userid):
        """
        Tries to return the name of a User on this Server by their id.
        Returns the name on success, empty string on failure.
        """
        users = server.members
        for user in users:
            if user.id == userid:
                return user.name
        return ""
    
    @commands.command(name="suggestions", pass_context=True)
    @checks.mod_or_permissions()
    async def suggestions_board(self, ctx):
        """Pretty-print the suggestions."""
        server = ctx.message.server
        msg="```md\n"
        for author in self.suggestions[server.id]:
            authorName = self._get_user_from_id(server, author)
            msg+="# "+authorName+"\n"
            for entry in self.suggestions[server.id][author]:
                # Discord message length is 2000, so cut the message length in chunks
                if (len(msg)+len(entry)) > 1500:
                        msg+="```"
                        await self.bot.say(msg)
                        msg="```md\n"
                msg+="* "+entry+"\n" 
            msg+="\n"
        msg+="```"
        await self.bot.say(msg)

    # The data model is...
    #   Server_id : { user_id : [ suggestion_string ] }
    @commands.command(aliases=["s", "suggest"], pass_context=True)
    async def suggestion(self, ctx, *, text):
        """Add a suggestion from any user"""
        serverId = ctx.message.server.id
        userId = ctx.message.author.id
        suggestion_string = ctx.message.content
        maxNum = self.settings["max suggestions"]
        if serverId not in self.suggestions:
            self.suggestions[serverId] = {}
        if userId not in self.suggestions[serverId]:
            self.suggestions[serverId][userId] = []
        index = len(self.suggestions[serverId][userId])+1
        if index > maxNum:
            await self.bot.say("You already have "+str(maxNum)+" suggestions!")
            return
        self.suggestions[serverId][userId].append( text )
        dataIO.save_json(self.suggestions_path, self.suggestions)
        await self.bot.say("Thank you for your contribution.")

def check_folder():
    if not os.path.exists("data/suggestions"):
        print("Creating data/suggestions folder...")
        os.makedirs("data/suggestions")

def check_file():
    f = "data/suggestions/suggestions.json"
    settings = "data/suggestions/settings.json"
    board = "data/suggestions/board.json"
    if not os.path.isfile(f):
        print("Creating default suggestions.json...")
        dataIO.save_json(f, {})
    if not os.path.isfile(settings):
        print("Creating empty settings.json...")
        dataIO.save_json(settings, {"max suggestions" : 10})
    if not os.path.isfile(board):
        print("Creating empty board.json...")
        dataIO.save_json(board, {})

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Suggestions(bot))

