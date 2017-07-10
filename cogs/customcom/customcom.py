import discord
from discord.ext import commands
from core import Config, checks
from core.utils.chat_formatting import box


import os
import re


class CustomCommands:
    """Custom commands
    Creates commands used to display text"""

    def __init__(self, bot):
        self.bot = bot
        self.file_path = "data/customcom/commands.json"
        self.c_commands = Config.get_conf(self.__class__.__name__,
                                          414589031223512)
        self.c_commands.register_guild(is_guild_enabled=False)
        self.c_commands.register_channel(is_channel_enabled=False)
        self.c_commands.register_member(is_member_enabled=False)
        self.c_commands.register_user(is_user_enabled=False)

    @commands.group(aliases=["cc"], pass_context=True, no_pm=True)
    @commands.guild_only()
    async def customcom(self, ctx: commands.Context):
        """Custom commands management"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @customcom.command(name="add", pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def cc_add(self, ctx, command: str, *, text):
        """Adds a custom command
        Example:
        [p]customcom add yourcommand Text you want
        CCs can be enhanced with arguments:
        https://twentysix26.github.io/Red-Docs/red_guide_command_args/
        """
        guild = ctx.message.guild
        command = command.lower()
        if command in self.bot.commands:
            await ctx.send("That command is already a standard command.")
            return
        if guild.id not in self.c_commands:
            self.c_commands[guild.id] = {}
        cmdlist = self.c_commands[guild.id]
        if command not in cmdlist:
            cmdlist[command] = text
            self.c_commands[guild.id] = cmdlist
            dataIO.save_json(self.file_path, self.c_commands)
            await ctx.send("Custom command successfully added.")
        else:
            await ctx.send("This command already exists. Use "
                           "`{}customcom edit` to edit it."
                           "".format(ctx.prefix))

    @customcom.command(name="edit", pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def cc_edit(self, ctx, command: str, *, text):
        """Edits a custom command
        Example:
        [p]customcom edit yourcommand Text you want
        """
        guild = ctx.message.guild
        command = command.lower()
        if guild.id in self.c_commands:
            cmdlist = self.c_commands[guild.id]
            if command in cmdlist:
                cmdlist[command] = text
                self.c_commands[guild.id] = cmdlist
                dataIO.save_json(self.file_path, self.c_commands)
                await ctx.send("Custom command successfully edited.")
            else:
                await ctx.send("That command doesn't exist. Use "
                               "`{}customcom add` to add it."
                               "".format(ctx.prefix))
        else:
            await ctx.send("There are no custom commands in this guild."
                           " Use `{}customcom add` to start adding some."
                           "".format(ctx.prefix))

    @customcom.command(name="delete", pass_context=True)
    @checks.mod_or_permissions(administrator=True)
    async def cc_delete(self, ctx, command: str):
        """Deletes a custom command
        Example:
        [p]customcom delete yourcommand"""
        guild = ctx.message.guild
        command = command.lower()
        if guild.id in self.c_commands:
            cmdlist = self.c_commands[guild.id]
            if command in cmdlist:
                cmdlist.pop(command, None)
                self.c_commands[guild.id] = cmdlist
                dataIO.save_json(self.file_path, self.c_commands)
                await ctx.send("Custom command successfully deleted.")
            else:
                await ctx.send("That command doesn't exist.")
        else:
            await ctx.send("There are no custom commands in this guild."
                           " Use `{}customcom add` to start adding some."
                           "".format(ctx.prefix))

    @customcom.command(name="list", pass_context=True)
    async def cc_list(self, ctx):
        """Shows custom commands list"""
        guild = ctx.message.guild
        commands = self.c_commands.get(guild.id, {})

        if not commands:
            await ctx.send("There are no custom commands in this guild."
                           " Use `{}customcom add` to start adding some."
                           "".format(ctx.prefix))
            return

        commands = ", ".join([ctx.prefix + c for c in sorted(commands)])
        commands = "Custom commands:\n\n" + commands

        if len(commands) < 1500:
            await ctx.send(box(commands))
        else:
            for page in pagify(commands, delims=[" ", "\n"]):
                await self.bot.whisper(box(page))

    async def on_message(self, message):
        is_private = isinstance(message.channel, discord.abc.PrivateChannel)
        if len(message.content) < 2 or is_private:
            return

        guild = message.guild
        prefix = self.get_prefix(message)

        if not prefix:
            return

        if guild.id in self.c_commands and self.bot.user_allowed(message):
            cmdlist = self.c_commands[guild.id]
            cmd = message.content[len(prefix):]
            if cmd in cmdlist:
                cmd = cmdlist[cmd]
                cmd = self.format_cc(cmd, message)
                await self.bot.send_message(message.channel, cmd)
            elif cmd.lower() in cmdlist:
                cmd = cmdlist[cmd.lower()]
                cmd = self.format_cc(cmd, message)
                await self.bot.send_message(message.channel, cmd)

    def get_prefix(self, message):
        for p in self.bot.settings.get_prefixes(message.guild):
            if message.content.startswith(p):
                return p
        return False

    def format_cc(self, command, message):
        results = re.findall("\{([^}]+)\}", command)
        for result in results:
            param = self.transform_parameter(result, message)
            command = command.replace("{" + result + "}", param)
        return command

    def transform_parameter(self, result, message):
        """
        For security reasons only specific objects are allowed
        Internals are ignored
        """
        raw_result = "{" + result + "}"
        objects = {
            "message": message,
            "author": message.author,
            "channel": message.channel,
            "guild": message.guild
        }
        if result in objects:
            return str(objects[result])
        try:
            first, second = result.split(".")
        except ValueError:
            return raw_result
        if first in objects and not second.startswith("_"):
            first = objects[first]
        else:
            return raw_result
        return str(getattr(first, second, raw_result))


def check_folders():
    if not os.path.exists("data/customcom"):
        print("Creating data/customcom folder...")
        os.makedirs("data/customcom")


def check_files():
    f = "data/customcom/commands.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty commands.json...")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(CustomCommands(bot))
