import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import os

class CustomCommands:
    """Custom commands."""

    def __init__(self, bot):
        self.bot = bot
        self.c_commands = fileIO("data/customcom/commands.json", "load")

    @checks.mod_or_permissions()
    @commands.command(pass_context=True, no_pm=True)
    async def addcom(self, ctx, command : str, *text):
        """Adds a custom command

        Example:
        !addcom yourcommand Text you want
        """
        if text == ():
            await self.bot.say("addcom [command] [text/url]")
            return
        server = ctx.message.server
        channel = ctx.message.channel
        text = " ".join(text)
        if not server.id in self.c_commands:
            self.c_commands[server.id] = {}
        cmdlist = self.c_commands[server.id]
        if command not in cmdlist:
            cmdlist[command] = text
            self.c_commands[server.id] = cmdlist
            fileIO("data/customcom/commands.json", "save", self.c_commands)
            await self.bot.say("`Custom command successfully added.`")
        else:
            await self.bot.say("`This command already exists. Use editcom to edit it.`")

    @checks.mod_or_permissions()
    @commands.command(pass_context=True, no_pm=True)
    async def editcom(self, ctx, command : str, *text):
        """Edits a custom command

        Example:
        !editcom yourcommand Text you want
        """
        if text == ():
            await self.bot.say("editcom [command] [text/url]")
            return
        server = ctx.message.server
        channel = ctx.message.channel
        text = " ".join(text)
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist[command] = text
                self.c_commands[server.id] = cmdlist
                fileIO("data/customcom/commands.json", "save", self.c_commands)
                await self.bot.say("`Custom command successfully edited.`")
            else:
                await self.bot.say("`That command doesn't exist. Use addcom [command] [text]`")
        else:
             await self.bot.say("`There are no custom commands in this server. Use addcom [command] [text]`")

    @checks.mod_or_permissions()
    @commands.command(pass_context=True, no_pm=True)
    async def delcom(self, ctx, command : str):
        """Deletes a custom command

        Example:
        !delcom yourcommand"""
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands[server.id] = cmdlist
                fileIO("data/customcom/commands.json", "save", self.c_commands)
                await self.bot.send_message(channel, "`Custom command successfully deleted.`")
            else:
                await self.bot.say("`That command doesn't exist.`")
        else:
            await self.bot.send_message(channel, "`There are no custom commands in this server. Use addcom [command] [text]`")

    async def checkCC(self, message):
        if message.author.id == self.bot.user.id or len(message.content) < 2 or message.channel.is_private:
            return
        msg = message.content
        server = message.server
        if msg[0] in self.bot.command_prefix and server.id in self.c_commands.keys():
            cmdlist = self.c_commands[server.id]
            if msg[1:] in cmdlist:
                await self.bot.send_message(message.channel, cmdlist[msg[1:]])

def check_folders():
    if not os.path.exists("data/customcom"):
        print("Creating data/customcom folder...")
        os.makedirs("data/customcom")

def check_files():
    f = "data/customcom/commands.json"
    if not fileIO(f, "check"):
        print("Creating empty commands.json...")
        fileIO(f, "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = CustomCommands(bot)
    bot.add_listener(n.checkCC, "on_message")
    bot.add_cog(n)