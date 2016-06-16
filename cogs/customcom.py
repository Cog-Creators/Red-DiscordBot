import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from __main__ import user_allowed, send_cmd_help
import os

class CustomCommands:
    """Custom commands."""

    def __init__(self, bot):
        self.bot = bot
        self.c_commands = fileIO("data/customcom/commands.json", "load")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def addcom(self, ctx, command : str, *, text):
        """Adds a custom command
        Supports arguments: author, server, channel
        
        Examples:
        !addcom yourcommand Text you want
        !addcom kickme :boot: {author.name}
        !addcom greet hi {author.mention}! welcome to {server.name}!
        !addcom whereami? you're in {channel.name}.. dumby
        !addcom id {author.id}
        """
        server = ctx.message.server
        command = command.lower()
        if command in self.bot.commands.keys():
            await self.bot.say("That command is already a standard command.")
            return
        if not server.id in self.c_commands:
            self.c_commands[server.id] = {}
        cmdlist = self.c_commands[server.id]
        if command not in cmdlist:
            cmdlist[command] = text
            self.c_commands[server.id] = cmdlist
            fileIO("data/customcom/commands.json", "save", self.c_commands)
            await self.bot.say("Custom command successfully added.. Testing")
            message = ctx.message
            try:
                await self.bot.say(text.format(message.author, message.server, message.channel, message, author=message.author, server=message.server, channel=message.channel, message=message))
            except Exception as e:
                print(e)
                await self.bot.say('Failed to send. Most likely incorrect format.')
        else:
            await self.bot.say("This command already exists. Use editcom to edit it.")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def editcom(self, ctx, command : str, *, text):
        """Edits a custom command

        Example:
        !editcom yourcommand Text you want
        """
        server = ctx.message.server
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist[command] = text
                self.c_commands[server.id] = cmdlist
                fileIO("data/customcom/commands.json", "save", self.c_commands)
                await self.bot.say("Custom command successfully edited.. Testing")
                message = ctx.message
                try:
                    await self.bot.say(text.format(message.author, message.server, message.channel, message, author=message.author, server=message.server, channel=message.channel, message=message))
                except Exception as e:
                    print(e)
                    await self.bot.say('Failed to send. Most likely incorrect format.')
            else:
                await self.bot.say("That command doesn't exist. Use addcom [command] [text]")
        else:
             await self.bot.say("There are no custom commands in this server. Use addcom [command] [text]")

    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(administrator=True)
    async def delcom(self, ctx, command : str):
        """Deletes a custom command

        Example:
        !delcom yourcommand"""
        server = ctx.message.server
        command = command.lower()
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands[server.id] = cmdlist
                fileIO("data/customcom/commands.json", "save", self.c_commands)
                await self.bot.say("Custom command successfully deleted.")
            else:
                await self.bot.say("That command doesn't exist.")
        else:
            await self.bot.say("There are no custom commands in this server. Use addcom [command] [text]")

    @commands.command(pass_context=True, no_pm=True)
    async def customcommands(self, ctx):
        """Shows custom commands list"""
        server = ctx.message.server
        if server.id in self.c_commands:
            cmdlist = self.c_commands[server.id]
            if cmdlist:
                i = 0
                msg = ["```Custom commands:\n"]
                for cmd in sorted([cmd for cmd in cmdlist.keys()]):
                    if len(msg[i]) + len(ctx.prefix) + len(cmd) + 5 > 2000:
                        msg[i] += "```"
                        i += 1
                        msg.append("``` {}{}\n".format(ctx.prefix, cmd))
                    else:
                        msg[i] += " {}{}\n".format(ctx.prefix, cmd)
                msg[i] += "```"
                for cmds in msg:
                    await self.bot.whisper(cmds)
            else:
                await self.bot.say("There are no custom commands in this server. Use addcom [command] [text]")
        else:
            await self.bot.say("There are no custom commands in this server. Use addcom [command] [text]")

    async def checkCC(self, message):
        if message.author.id == self.bot.user.id or len(message.content) < 2 or message.channel.is_private:
            return

        if not user_allowed(message):
            return

        msg = message.content
        server = message.server
        prefix = self.get_prefix(msg)

        if prefix and server.id in self.c_commands.keys():
            cmdlist = self.c_commands[server.id]
            cmd = msg[len(prefix):]
            response = None
            if cmd in cmdlist.keys():
                response = cmdlist[cmd]
            elif cmd.lower() in cmdlist.keys():
                response = cmdlist[cmd.lower()]
            if response:
                await self.bot.send_message(message.channel, response.format(message.author, message.server, message.channel, message, author=message.author, server=message.server, channel=message.channel, message=message))

    def get_prefix(self, msg):
        for p in self.bot.command_prefix:
            if msg.startswith(p):
                return p
        return False

def check_folders():
    if not os.path.exists("data/customcom"):
        print("Creating data/customcom folder...")
        os.makedirs("data/customcom")

def check_files(bot):
    f = "data/customcom/commands.json"
    if not fileIO(f, "check"):
        print("Creating empty commands.json...")
        fileIO(f, "save", {"FORMAT":True})
        return
    print('hi')
    current = fileIO(f, "load")
    if "FORMAT" not in current: # consistency check
        print("Custom Commands have been updated with format string support.")
        print("Updating old custom commands. Any brackets {} found will be escaped {{}}")
        for sid, commands in current.items():
            msg = ""
            for cmd, response in commands.items():
                if "{" in response or "}" in response:
                    commands[cmd] = response.replace("{","{{").replace("}","}}")
                    #use [p] if loaded before settings/prefixes were
                    pfx = "[p]" if bot.command_prefix[0] == "_" else bot.command_prefix[0]
                    msg += "{}{}\n".format(pfx,cmd)
            if msg:
                # can't get server cause not logged in..
                svr = bot.get_server(sid)
                if svr is None:
                    svr = sid
                print("Server: {0} - custom commands altered:\n{2}{1}{2}".format(svr, msg, "--------\n"))
        current["FORMAT"] = True
        fileIO(f, "save", current)

def setup(bot):
    check_folders()
    check_files(bot)
    n = CustomCommands(bot)
    bot.add_listener(n.checkCC, "on_message")
    bot.add_cog(n)
