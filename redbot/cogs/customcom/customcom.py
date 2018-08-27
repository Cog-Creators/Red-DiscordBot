import os
import re
import random
from datetime import datetime
from inspect import Parameter
from collections import OrderedDict
from typing import Mapping

import discord

from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.i18n import Translator, cog_i18n

_ = Translator("CustomCommands", __file__)


class CCError(Exception):
    pass


class NotFound(CCError):
    pass


class AlreadyExists(CCError):
    pass


class CommandObj:
    def __init__(self, **kwargs):
        config = kwargs.get("config")
        self.bot = kwargs.get("bot")
        self.db = config.guild

    @staticmethod
    async def get_commands(config) -> dict:
        commands = await config.commands()
        customcommands = {k: v for k, v in commands.items() if commands[k]}
        if len(customcommands) == 0:
            return None
        return customcommands

    async def get_responses(self, ctx):
        intro = _(
            "Welcome to the interactive random {} maker!\n"
            "Every message you send will be added as one of the random "
            "responses to choose from once this {} is "
            "triggered. To exit this interactive menu, type `{}`"
        ).format("customcommand", "customcommand", "exit()")
        await ctx.send(intro)

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.message.author

        responses = []
        while True:
            await ctx.send(_("Add a random response:"))
            msg = await self.bot.wait_for("message", check=check)

            if msg.content.lower() == "exit()":
                break
            else:
                responses.append(msg.content)
        return responses

    def get_now(self) -> str:
        # Get current time as a string, for 'created_at' and 'edited_at' fields
        # in the ccinfo dict
        return "{:%d/%m/%Y %H:%M:%S}".format(datetime.utcnow())

    async def get(self, message: discord.Message, command: str) -> str:
        ccinfo = await self.db(message.guild).commands.get_raw(command, default=None)
        if not ccinfo:
            raise NotFound
        else:
            return ccinfo["response"]

    async def create(self, ctx: commands.Context, command: str, response):
        """Create a custom command"""
        # Check if this command is already registered as a customcommand
        if await self.db(ctx.guild).commands.get_raw(command, default=None):
            raise AlreadyExists()
        author = ctx.message.author
        ccinfo = {
            "author": {"id": author.id, "name": author.name},
            "command": command,
            "created_at": self.get_now(),
            "editors": [],
            "response": response,
        }
        await self.db(ctx.guild).commands.set_raw(command, value=ccinfo)

    async def edit(self, ctx: commands.Context, command: str, response: None):
        """Edit an already existing custom command"""
        # Check if this command is registered
        if not await self.db(ctx.guild).commands.get_raw(command, default=None):
            raise NotFound()

        author = ctx.message.author
        ccinfo = await self.db(ctx.guild).commands.get_raw(command, default=None)

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.message.author

        if not response:
            await ctx.send(_("Do you want to create a 'randomized' cc? {}").format("y/n"))

            msg = await self.bot.wait_for("message", check=check)
            if msg.content.lower() == "y":
                response = await self.get_responses(ctx=ctx)
            else:
                await ctx.send(_("What response do you want?"))
                response = (await self.bot.wait_for("message", check=check)).content

        ccinfo["response"] = response
        ccinfo["edited_at"] = self.get_now()

        if author.id not in ccinfo["editors"]:
            # Add the person who invoked the `edit` coroutine to the list of
            # editors, if the person is not yet in there
            ccinfo["editors"].append(author.id)

        await self.db(ctx.guild).commands.set_raw(command, value=ccinfo)

    async def delete(self, ctx: commands.Context, command: str):
        """Delete an already exisiting custom command"""
        # Check if this command is registered
        if not await self.db(ctx.guild).commands.get_raw(command, default=None):
            raise NotFound()
        await self.db(ctx.guild).commands.set_raw(command, value=None)


@cog_i18n(_)
class CustomCommands:
    """Custom commands

    Creates commands used to display text"""

    def __init__(self, bot):
        self.bot = bot
        self.key = 414589031223512
        self.config = Config.get_conf(self, self.key)
        self.config.register_guild(commands={})
        self.commandobj = CommandObj(config=self.config, bot=self.bot)

    @commands.group(aliases=["cc"])
    @commands.guild_only()
    async def customcom(self, ctx: commands.Context):
        """Custom commands management"""
        pass

    @customcom.group(name="add")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add(self, ctx: commands.Context):
        """
        CCs can be enhanced with arguments:

        Argument    What it will be substituted with

        {message}   message

        {author}    message.author

        {channel}   message.channel

        {guild}     message.guild

        {server}    message.guild

        {0},{1},... a user-provided argument
        """
        pass

    @cc_add.command(name="random")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add_random(self, ctx: commands.Context, command: str):
        """
        Create a CC where it will randomly choose a response!

        Note: This is interactive
        """
        responses = []

        responses = await self.commandobj.get_responses(ctx=ctx)
        try:
            await self.commandobj.create(ctx=ctx, command=command, response=responses)
            await ctx.send(_("Custom command successfully added."))
        except AlreadyExists:
            await ctx.send(
                _("This command already exists. Use `{}` to edit it.").format(
                    "{}customcom edit".format(ctx.prefix)
                )
            )

        # await ctx.send(str(responses))

    @cc_add.command(name="simple")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add_simple(self, ctx, command: str, *, text):
        """Adds a simple custom command

        Example:
        [p]customcom add simple yourcommand Text you want
        """
        command = command.lower()
        if command in self.bot.all_commands:
            await ctx.send(_("That command is already a standard command."))
            return
        try:
            await self.commandobj.create(ctx=ctx, command=command, response=text)
            await ctx.send(_("Custom command successfully added."))
        except AlreadyExists:
            await ctx.send(
                _("This command already exists. Use `{}` to edit it.").format(
                    "{}customcom edit".format(ctx.prefix)
                )
            )

    @customcom.command(name="edit")
    @checks.mod_or_permissions(administrator=True)
    async def cc_edit(self, ctx, command: str, *, text=None):
        """Edits a custom command

        Example:
        [p]customcom edit yourcommand Text you want
        """
        command = command.lower()

        try:
            await self.commandobj.edit(ctx=ctx, command=command, response=text)
            await ctx.send(_("Custom command successfully edited."))
        except NotFound:
            await ctx.send(
                _("That command doesn't exist. Use `{}` to add it.").format(
                    "{}customcom add".format(ctx.prefix)
                )
            )

    @customcom.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def cc_delete(self, ctx, command: str):
        """Deletes a custom command
        Example:
        [p]customcom delete yourcommand"""
        command = command.lower()
        try:
            await self.commandobj.delete(ctx=ctx, command=command)
            await ctx.send(_("Custom command successfully deleted."))
        except NotFound:
            await ctx.send(_("That command doesn't exist."))

    @customcom.command(name="list")
    async def cc_list(self, ctx):
        """Shows custom commands list"""

        response = await CommandObj.get_commands(self.config.guild(ctx.guild))

        if not response:
            await ctx.send(
                _(
                    "There are no custom commands in this server."
                    " Use `{}` to start adding some."
                ).format("{}customcom add".format(ctx.prefix))
            )
            return

        results = []

        for command, body in response.items():
            responses = body["response"]
            if isinstance(responses, list):
                result = ", ".join(responses)
            elif isinstance(responses, str):
                result = responses
            else:
                continue
            results.append("{command:<15} : {result}".format(command=command, result=result))

        commands = "\n".join(results)

        if len(commands) < 1500:
            await ctx.send(box(commands))
        else:
            for page in pagify(commands, delims=[" ", "\n"]):
                await ctx.author.send(box(page))

    async def on_message(self, message):
        is_private = isinstance(message.channel, discord.abc.PrivateChannel)

        # user_allowed check, will be replaced with self.bot.user_allowed or
        # something similar once it's added

        user_allowed = True
        if len(message.content) < 2 or is_private or not user_allowed or message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        if not ctx.prefix or ctx.valid:
            return

        try:
            raw_response = await self.commandobj.get(message=message, command=ctx.invoked_with)
            if isinstance(raw_response, list):
                raw_response = random.choice(raw_response)
            elif isinstance(raw_response, str):
                pass
            else:
                raise NotFound()
        except NotFound:
            return
        await self.call_cc_command(ctx, raw_response, message)

    async def call_cc_command(self, ctx, raw_response, message) -> None:
        # wrap the command here so it won't register with the bot
        fake_cc = commands.Command(ctx.invoked_with, self.cc_callback)
        fake_cc.params = self.prepare_args(raw_response)
        ctx.command = fake_cc
        await self.bot.invoke(ctx)
        if not ctx.command_failed:
            await self.cc_command(*ctx.args, **ctx.kwargs, raw_response=raw_response)

    async def cc_callback(self, *args, **kwargs) -> None:
        """
        Custom command.

        Created via the CustomCom cog. See `[p]customcom` for more details.
        """
        # fake command to take advantage of discord.py's parsing and events
        pass

    async def cc_command(self, ctx, *cc_args, raw_response, **cc_kwargs) -> None:
        cc_args = (*cc_args, *cc_kwargs.values())
        results = re.findall(r"\{([^}]+)\}", raw_response)
        for result in results:
            param = self.transform_parameter(result, ctx.message)
            raw_response = raw_response.replace("{" + result + "}", param)
        results = re.findall(r"\{((\d+)[^\.}]*(\.[^:}]+)?[^}]*)\}", raw_response)
        for result in results:
            index = int(result[1])
            arg = self.transform_arg(result[0], result[2], cc_args[index])
            raw_response = raw_response.replace("{" + result[0] + "}", arg)
        await ctx.send(raw_response)

    def prepare_args(self, raw_response) -> Mapping[str, Parameter]:
        args = re.findall(r"\{(\d+)[^:}]*(:[^\.}]*)?[^}]*\}", raw_response)
        if not args:
            return OrderedDict([["ctx", Parameter("ctx", Parameter.POSITIONAL_OR_KEYWORD)]])
        allowed_builtins = {
            "bool": bool,
            "complex": complex,
            "float": float,
            "frozenset": frozenset,
            "int": int,
            "list": list,
            "set": set,
            "str": str,
            "tuple": tuple,
        }
        highest = max(int(a[0]) for a in args)
        fin = [
            Parameter("_" + str(i), Parameter.POSITIONAL_OR_KEYWORD) for i in range(highest + 1)
        ]
        for arg in args:
            index = int(arg[0])
            if fin[index].annotation is not Parameter.empty:
                continue
            anno = arg[1][1:]
            if anno.lower().endswith("converter"):
                anno = anno[:-9]
            if not anno or anno.startswith("_"):  # public types only
                name = "{}_{}".format("text", index if index < highest else "final")
                fin[index] = fin[index].replace(name=name)
                continue
            # allow type hinting only for discord.py and builtin types
            try:
                anno = getattr(discord, anno)
                # force an AttributeError if there's no discord.py converter
                getattr(commands.converter, anno.__name__ + "Converter")
            except AttributeError:
                anno = allowed_builtins.get(anno.lower(), Parameter.empty)
            name = "{}_{}".format(
                "text" if anno is Parameter.empty else anno.__name__.lower(),
                index if index < highest else "final",
            )
            fin[index] = fin[index].replace(name=name, annotation=anno)
        # consume rest
        fin[-1] = fin[-1].replace(kind=Parameter.KEYWORD_ONLY)
        # insert ctx parameter for discord.py parsing
        fin = [Parameter("ctx", Parameter.POSITIONAL_OR_KEYWORD)] + fin
        return OrderedDict((p.name, p) for p in fin)

    def transform_arg(self, result, attr, obj) -> str:
        attr = attr[1:]
        if not attr:
            return str(obj)
        raw_result = "{" + result + "}"
        # forbid private members and nested attr lookups
        if attr.startswith("_") or "." in attr:
            return raw_result
        return str(getattr(obj, attr, raw_result))

    def transform_parameter(self, result, message) -> str:
        """
        For security reasons only specific objects are allowed
        Internals are ignored
        """
        raw_result = "{" + result + "}"
        objects = {
            "message": message,
            "author": message.author,
            "channel": message.channel,
            "guild": message.guild,
            "server": message.guild,
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
