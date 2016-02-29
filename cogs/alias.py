import discord
from discord.ext import commands
from .utils.chat_formatting import *
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
import os

class Alias:
    def __init__(self,bot):
        self.bot = bot
        self.aliases = fileIO("data/alias/aliases.json","load")

    @commands.group(pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def alias(self,ctx):
        """Manage per-server aliases for commands"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @alias.command(name="add",pass_context=True)
    async def _add_alias(self,ctx,command : str,*,to_execute):
        """Add an alias for a command

           Example: !alias add test flip @Twentysix"""
        server = ctx.message.server
        if self.get_prefix(to_execute) == False:
            to_execute = self.bot.command_prefix[0] + to_execute
        if server.id not in self.aliases:
            self.aliases[server.id] = {}
        #curr_aliases = self.aliases[server.id]
        if command not in self.bot.commands:
            self.aliases[server.id][command] = to_execute
            fileIO("data/alias/aliases.json","save",self.aliases)
            await self.bot.say("Alias '{}' added.".format(command))
        else:
            await self.bot.say("Cannot add '{}' because it's a real bot command.".format(command))        

    @alias.command(name="help",pass_context=True)
    async def _help_alias(self,ctx,command):
        """Tries to execute help for the base command of the alias"""
        server = ctx.message.server
        if server.id in self.aliases:
            server_aliases = self.aliases[server.id]
            if command in server_aliases:
                help_cmd = server_aliases[command].split(" ")[0]
                new_content = self.bot.command_prefix[0]
                new_content += "help "
                new_content += help_cmd[len(self.get_prefix(help_cmd)):]
                message = ctx.message
                message.content = new_content
                await self.bot.process_commands(message)
            else:
                await self.bot.say("That alias doesn't exist.")

    @alias.command(name="show",pass_context=True)
    async def _show_alias(self,ctx,command):
        """Shows what command the alias executes."""
        server = ctx.message.server
        if server.id in self.aliases:
            server_aliases = self.aliases[server.id]
            if command in server_aliases:
                await self.bot.say(box(server_aliases[command]))
            else:
                await self.bot.say("That alias doesn't exist.")

    @alias.command(name="del",pass_context=True)
    async def _del_alias(self,ctx,command : str):
        """Deletes an alias"""
        server = ctx.message.server
        if server.id in self.aliases:
            self.aliases[server.id].pop(command,None)
            fileIO("data/alias/aliases.json","save",self.aliases)
        await self.bot.say("Alias '{}' deleted.".format(command))

    async def check_aliases(self,message):
        if message.author.id == self.bot.user.id or len(message.content) < 2 or message.channel.is_private:
            return

        msg = message.content
        server = message.server
        prefix = self.get_prefix(msg)

        if prefix and server.id in self.aliases:
            aliaslist = self.aliases[server.id]
            alias = msg[len(prefix):].split(" ")[0]
            args = msg[len(self.first_word(message.content)):]
            if alias in aliaslist.keys():
                content = aliaslist[alias] + args
                new_message = message
                new_message.content = content
                await self.bot.process_commands(new_message)

    def first_word(self,msg):
        return msg.split(" ")[0]

    def get_prefix(self, msg):
        for p in self.bot.command_prefix:
            if msg.startswith(p):
                return p
        return False

def check_folder():
    if not os.path.exists("data/alias"):
        print("Creating data/alias folder...")
        os.makedirs("data/alias")

def check_file():
    aliases = {}

    f = "data/alias/aliases.json"
    if not fileIO(f, "check"):
        print("Creating default alias's aliases.json...")
        fileIO(f, "save", aliases)

def setup(bot):
    check_folder()
    check_file()
    n = Alias(bot)
    bot.add_listener(n.check_aliases, "on_message")
    bot.add_cog(n)