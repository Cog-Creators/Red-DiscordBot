import discord
from discord.ext import commands
from core import Config, checks
from core.utils.chat_formatting import box


import os
import re

# ASK HOW TO RETREIVE THE WHOLE CONFIG!!!!!


class CustomCommands:
    """Custom commands
    Creates commands used to display text"""

    def __init__(self, bot):
        self.bot = bot
        self.key = 414589031223512
        self.config = Config.get_conf(self.__class__.__name__,
                                      self.key)
        self.config.register_guild()

    @commands.group(aliases=["cc"], no_pm=True)
    @commands.guild_only()
    async def customcom(self, ctx: commands.Context):
        """Custom commands management"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @customcom.command(name="add")
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
        if command in self.bot.all_commands:
            await ctx.send("That command is already a standard command.")
            return
        # self.config.register_guild() takes care of this
        # if guild.id not in self.c_commands:
        #     self.c_commands[guild.id] = {}
        if not self.config.guild(ctx.guild).get(command):
            await self.config.guild(ctx.guild).set(command, text)
            await ctx.send("Custom command successfully added.")
        else:
            await ctx.send("This command already exists. Use "
                           "`{}customcom edit` to edit it."
                           "".format(ctx.prefix))

    @customcom.command(name="edit")
    @checks.mod_or_permissions(administrator=True)
    async def cc_edit(self, ctx, command: str, *, text):
        """Edits a custom command
        Example:
        [p]customcom edit yourcommand Text you want
        """
        guild = ctx.message.guild
        command = command.lower()
        cmdlist = self.c_commands[guild.id]
        if self.config.guild(ctx.guild).get(command):
            await self.config.guild(ctx.guild).set(command, text)
            await ctx.send("Custom command successfully edited.")
        else:
            await ctx.send("That command doesn't exist. Use "
                           "`{}customcom add` to add it."
                           "".format(ctx.prefix))

        # If there are no custom commands in this guild
        # await ctx.send("There are no custom commands in this guild."
        #                " Use `{}customcom add` to start adding some."
        #                "".format(ctx.prefix))

    @customcom.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def cc_delete(self, ctx, command: str):
        """Deletes a custom command
        Example:
        [p]customcom delete yourcommand"""
        guild = ctx.message.guild
        command = command.lower()

        if self.config.guild(ctx.guild).get(command):
            await self.config.guild(ctx.guild).set(command, None)
            await ctx.send("Custom command successfully deleted.")
        else:
            await ctx.send("That command doesn't exist.")
        # If there are no custom commands in this guild
        # await ctx.send("There are no custom commands in this guild."
        #                " Use `{}customcom add` to start adding some."
        #                "".format(ctx.prefix))

    @customcom.command(name="list")
    async def cc_list(self, ctx):
        """Shows custom commands list"""

        await ctx.send("Not available yet. Sorry.")

        return

        guild = ctx.message.guild

        # Need info on grabbing whole config for guild

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
        prefixes = self.bot.db.guild(message.guild).get('prefix')

        if len(prefixes) < 1:
            return

        # user_allowed check, will be replaced with self.bot.user_allowed or
        # something similar once it's added

        user_allowed = True

        for prefix in prefixes:
            if message.content.startswith(prefix):
                break
        else:
            return

        if user_allowed:
            cmd = message.content[len(prefix):]
            regular = self.config.guild(message.guild).get(cmd)
            lowercase = self.config.guild(message.guild).get(cmd.lower())
            if regular:
                cmd = regular
                cmd = self.format_cc(cmd, message)
                await message.channel.send(cmd)
            elif lowercase:
                cmd = lowercase
                cmd = self.format_cc(cmd, message)
                await message.channel.send(cmd)

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


def setup(bot):

    bot.add_cog(CustomCommands(bot))
