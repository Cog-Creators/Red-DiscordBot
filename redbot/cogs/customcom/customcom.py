import os
import re
import random
from datetime import datetime

import discord
from discord.ext import commands

from redbot.core import Config, checks
from redbot.core.utils.chat_formatting import box


class CCError(Exception):
    pass


class NotFound(CCError):
    pass


class AlreadyExists(CCError):
    pass


class CommandObj:

    def __init__(self, **kwargs):
        config = kwargs.get('config')
        self.bot = kwargs.get('bot')
        self.db = config.guild

    @staticmethod
    async def get_commands(config) -> dict:
        commands = await config.commands()
        customcommands = {k: v for k, v in commands.items() if commands[k]}
        if len(customcommands) == 0:
            return None
        return customcommands

    async def get_responses(self, ctx):
        intro = ("Welcome to the interactive random customcommand maker!\n"
                 "Every message you send will be added as one of the random "
                 "response to choose from once this customcommand is "
                 "triggered. To exit this interactive menu, type `exit()`")
        await ctx.send(intro)

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.message.author
        responses = []
        while True:
            await ctx.send("Add a random response:")
            msg = await self.bot.wait_for('message', check=check)

            if msg.content.lower() == 'exit()':
                break
            else:
                responses.append(msg.content)
        return responses

    def get_now(self) -> str:
        # Get current time as a string, for 'created_at' and 'edited_at' fields
        # in the ccinfo dict
        return '{:%d/%m/%Y %H:%M:%S}'.format(datetime.utcnow())

    async def get(self,
                  message: discord.Message,
                  command: str) -> str:
        ccinfo = await self.db(message.guild).commands.get_attr(command)
        if not ccinfo:
            raise NotFound
        else:
            return ccinfo['response']

    async def create(self,
                     ctx: commands.Context,
                     command: str,
                     response):
        """Create a customcommand"""
        # Check if this command is already registered as a customcommand
        if await self.db(ctx.guild).commands.get_attr(command):
            raise AlreadyExists()
        author = ctx.message.author
        ccinfo = {
            'author': {
                'id': author.id,
                'name': author.name
            },
            'command': command,
            'created_at': self.get_now(),
            'editors': [],
            'response': response

        }
        await self.db(ctx.guild).commands.set_attr(command,
                                                   ccinfo)

    async def edit(self,
                   ctx: commands.Context,
                   command: str,
                   response: None):
        """Edit an already existing custom command"""
        # Check if this command is registered
        if not await self.db(ctx.guild).commands.get_attr(command):
            raise NotFound()

        author = ctx.message.author
        ccinfo = await self.db(ctx.guild).commands.get_attr(command)

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.message.author

        if not response:
            await ctx.send("Do you want to create a 'randomized' cc? y/n")

            msg = await self.bot.wait_for('message', check=check)
            if msg.content.lower() == 'y':
                response = await self.get_responses(ctx=ctx)
            else:
                await ctx.send("What response do you want?")
                response = (await self.bot.wait_for(
                    'message', check=check)
                ).content

        ccinfo['response'] = response
        ccinfo['edited_at'] = self.get_now()

        if author.id not in ccinfo['editors']:
            # Add the person who invoked the `edit` coroutine to the list of
            # editors, if the person is not yet in there
            ccinfo['editors'].append(
                author.id
            )

        await self.db(ctx.guild).commands.set_attr(command,
                                                   ccinfo)

    async def delete(self,
                     ctx: commands.Context,
                     command: str):
        """Delete an already exisiting custom command"""
        # Check if this command is registered
        if not await self.db(ctx.guild).commands.get_attr(command):
            raise NotFound()
        await self.db(ctx.guild).commands.set_attr(command,
                                                   None)


class CustomCommands:
    """Custom commands
    Creates commands used to display text"""

    def __init__(self, bot):
        self.bot = bot
        self.key = 414589031223512
        self.config = Config.get_conf(self,
                                      self.key)
        self.config.register_guild(commands={})
        self.commandobj = CommandObj(config=self.config,
                                     bot=self.bot)

    @commands.group(aliases=["cc"], no_pm=True)
    @commands.guild_only()
    async def customcom(self,
                        ctx: commands.Context):
        """Custom commands management"""
        if not ctx.invoked_subcommand:
            await self.bot.send_cmd_help(ctx)

    @customcom.group(name="add")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add(self,
                     ctx: commands.Context):
        """
        CCs can be enhanced with arguments:
        https: // twentysix26.github.io / Red - Docs / red_guide_command_args/
        """
        if not ctx.invoked_subcommand or isinstance(ctx.invoked_subcommand,
                                                    commands.Group):
            await self.bot.send_cmd_help(ctx)

    @cc_add.command(name='random')
    @checks.mod_or_permissions(administrator=True)
    async def cc_add_random(self,
                            ctx: commands.Context,
                            command: str):
        """
        Create a CC where it will randomly choose a response!
        Note: This is interactive
        """
        channel = ctx.channel
        responses = []

        responses = await self.commandobj.get_responses(ctx=ctx)
        try:
            await self.commandobj.create(ctx=ctx,
                                         command=command,
                                         response=responses)
            await ctx.send("Custom command successfully added.")
        except AlreadyExists:
            await ctx.send("This command already exists. Use "
                           "`{}customcom edit` to edit it."
                           "".format(ctx.prefix))

        # await ctx.send(str(responses))

    @cc_add.command(name="simple")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add_simple(self,
                            ctx,
                            command: str,
                            *,
                            text):
        """Adds a simple custom command
        Example:
        [p]customcom add simple yourcommand Text you want
        """
        guild = ctx.guild
        command = command.lower()
        if command in self.bot.all_commands:
            await ctx.send("That command is already a standard command.")
            return
        try:
            await self.commandobj.create(ctx=ctx,
                                         command=command,
                                         response=text)
            await ctx.send("Custom command successfully added.")
        except AlreadyExists:
            await ctx.send("This command already exists. Use "
                           "`{}customcom edit` to edit it."
                           "".format(ctx.prefix))

    @customcom.command(name="edit")
    @checks.mod_or_permissions(administrator=True)
    async def cc_edit(self,
                      ctx,
                      command: str,
                      *,
                      text=None):
        """Edits a custom command
        Example:
        [p]customcom edit yourcommand Text you want
        """
        guild = ctx.message.guild
        command = command.lower()

        try:
            await self.commandobj.edit(ctx=ctx,
                                       command=command,
                                       response=text)
            await ctx.send("Custom command successfully edited.")
        except NotFound:
            await ctx.send("That command doesn't exist. Use "
                           "`{}customcom add` to add it."
                           "".format(ctx.prefix))

    @customcom.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def cc_delete(self,
                        ctx,
                        command: str):
        """Deletes a custom command
        Example:
        [p]customcom delete yourcommand"""
        guild = ctx.message.guild
        command = command.lower()
        try:
            await self.commandobj.delete(ctx=ctx,
                                         command=command)
            await ctx.send("Custom command successfully deleted.")
        except NotFound:
            await ctx.send("That command doesn't exist.")

    @customcom.command(name="list")
    async def cc_list(self,
                      ctx):
        """Shows custom commands list"""

        response = await CommandObj.get_commands(self.config.guild(ctx.guild))

        if not response:
            await ctx.send("There are no custom commands in this guild."
                           " Use `{}customcom add` to start adding some."
                           "".format(ctx.prefix))
            return

        results = []

        for command, body in response.items():
            responses = body['response']
            if isinstance(responses, list):
                result = ", ".join(responses)
            elif isinstance(responses, str):
                result = responses
            else:
                continue
            results.append("{command:<15} : {result}".format(command=command,
                                                             result=result))

        commands = "\n".join(results)

        if len(commands) < 1500:
            await ctx.send(box(commands))
        else:
            for page in pagify(commands, delims=[" ", "\n"]):
                await self.bot.whisper(box(page))

    async def on_message(self,
                         message):
        is_private = isinstance(message.channel, discord.abc.PrivateChannel)
        if len(message.content) < 2 or is_private:
            return

        guild = message.guild
        prefixes = await self.bot.db.guild(message.guild).get_attr('prefix')

        if len(prefixes) < 1:
            def_prefixes = await self.bot.get_prefix(message)
            for prefix in def_prefixes:
                prefixes.append(prefix)

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
            try:
                c = await self.commandobj.get(message=message,
                                              command=cmd)
                if isinstance(c, list):
                    command = random.choice(c)
                elif isinstance(c, str):
                    command = c
                else:
                    raise NotFound()
            except NotFound:
                return
            response = self.format_cc(command, message)
            await message.channel.send(response)

    def format_cc(self,
                  command,
                  message) -> str:
        results = re.findall("\{([^}]+)\}", command)
        for result in results:
            param = self.transform_parameter(result, message)
            command = command.replace("{" + result + "}", param)
        return command

    def transform_parameter(self,
                            result,
                            message) -> str:
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
