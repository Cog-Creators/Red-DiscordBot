import os
import re
import random
from datetime import datetime, timedelta
from inspect import Parameter
from collections import OrderedDict
from typing import Mapping

import discord

from redbot.core import Config, checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.i18n import Translator, cog_i18n

from .customcommand import custom_command

_ = Translator("CustomCommands", __file__)


class CCError(Exception):
    pass


class AlreadyExists(CCError):
    pass


class ArgParseError(CCError):
    pass


class NotFound(CCError):
    pass


class OnCooldown(CCError):
    pass


class CommandObj:
    def __init__(self, **kwargs):
        self.cog = kwargs.get("cog")
        self.bot = kwargs.get("bot")
        self.db = self.cog.config.guild

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
        args = None
        while True:
            await ctx.send(_("Add a random response:"))
            msg = await self.bot.wait_for("message", check=check)

            if msg.content.lower() == "exit()":
                break
            else:
                try:
                    this_args = ctx.cog.prepare_args(msg.content)
                except ArgParseError as e:
                    await ctx.send(e.args[0])
                    continue
                if args and args != this_args:
                    await ctx.send(_("Random responses must take the same arguments!"))
                    continue
                args = args or this_args
                responses.append(msg.content)
        return responses

    def get_now(self) -> str:
        # Get current time as a string, for 'created_at' and 'edited_at' fields
        # in the ccinfo dict
        return "{:%d/%m/%Y %H:%M:%S}".format(datetime.utcnow())

    async def get(self, message: discord.Message, command: str) -> str:
        ccinfo = await self.db(message.guild).commands.get_raw(command, default=None)
        if not ccinfo:
            raise NotFound()
        else:
            return ccinfo["response"], ccinfo.get("cooldowns", {})

    async def create(self, ctx: commands.Context, command: str, *, response):
        """Create a custom command"""
        # Check if this command is already registered as a customcommand
        if await self.db(ctx.guild).commands.get_raw(command, default=None):
            raise AlreadyExists()
        # test to raise
        ctx.cog.prepare_args(response if isinstance(response, str) else response[0])
        author = ctx.message.author
        ccinfo = {
            "author": {"id": author.id, "name": author.name},
            "command": command,
            "cooldowns": {},
            "created_at": self.get_now(),
            "editors": [],
            "response": response,
        }
        await self.db(ctx.guild).commands.set_raw(command, value=ccinfo)
        self.cog.register_cc(command)

    async def edit(
        self,
        ctx: commands.Context,
        command: str,
        *,
        response=None,
        cooldowns: Mapping[str, int] = None,
        ask_for: bool = True
    ):
        """Edit an already existing custom command"""
        ccinfo = await self.db(ctx.guild).commands.get_raw(command, default=None)

        # Check if this command is registered
        if not ccinfo:
            raise NotFound()

        author = ctx.message.author

        def check(m):
            return m.channel == ctx.channel and m.author == ctx.author

        if ask_for and not response:
            await ctx.send(_("Do you want to create a 'randomized' cc? {}").format("y/n"))

            msg = await self.bot.wait_for("message", check=check)
            if msg.content.lower() == "y":
                response = await self.get_responses(ctx=ctx)
            else:
                await ctx.send(_("What response do you want?"))
                response = (await self.bot.wait_for("message", check=check)).content

        if response:
            # test to raise
            ctx.cog.prepare_args(response if isinstance(response, str) else response[0])
            ccinfo["response"] = response

        if cooldowns:
            ccinfo.setdefault("cooldowns", {}).update(cooldowns)
            for key, value in ccinfo["cooldowns"].copy().items():
                if value <= 0:
                    del ccinfo["cooldowns"][key]

        if author.id not in ccinfo["editors"]:
            # Add the person who invoked the `edit` coroutine to the list of
            # editors, if the person is not yet in there
            ccinfo["editors"].append(author.id)

        ccinfo["edited_at"] = self.get_now()

        await self.db(ctx.guild).commands.set_raw(command, value=ccinfo)

    async def delete(self, ctx: commands.Context, command: str):
        """Delete an already exisiting custom command"""
        # Check if this command is registered
        if not await self.db(ctx.guild).commands.get_raw(command, default=None):
            raise NotFound()
        await self.db(ctx.guild).commands.set_raw(command, value=None)
        ctx.cog.unregister_cc(command)


@cog_i18n(_)
class CustomCommands(commands.Cog):
    """Custom commands

    Creates commands used to display text"""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.cc_map = bot.get_cog_map(self)
        self.key = 414589031223512
        self.config = Config.get_conf(self, self.key)
        self.config.register_guild(commands={})
        self.commandobj = CommandObj(cog=self, bot=self.bot)
        self.cooldowns = {}

    async def initialize(self):
        all_cc = await self.config.all_guilds()
        for commands in all_cc.values():
            for name in commands["commands"].keys():
                self.register_cc(name)

    def register_cc(self, name: str) -> None:
        self.cc_map.setdefault(name, self.__cc_command)

    def unregister_cc(self, name: str) -> None:
        self.cc_map.pop(name, None)

    @commands.group(aliases=["cc"])
    @commands.guild_only()
    async def customcom(self, ctx: commands.Context):
        """Custom commands management"""
        pass

    @customcom.group(name="add")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add(self, ctx: commands.Context):
        """
        Adds a new custom command

        CCs can be enhanced with arguments:
        https://red-discordbot.readthedocs.io/en/v3-develop/cog_customcom.html
        """
        pass

    @cc_add.command(name="random")
    @checks.mod_or_permissions(administrator=True)
    async def cc_add_random(self, ctx: commands.Context, command: str.lower):
        """
        Create a CC where it will randomly choose a response!

        Note: This is interactive
        """
        if command in self.bot.core_map:
            return await ctx.send(_("That command is already a standard command."))

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
    async def cc_add_simple(self, ctx, command: str.lower, *, text: str):
        """Adds a simple custom command

        Example:
        [p]customcom add simple yourcommand Text you want
        """
        if command in self.bot.core_map:
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
        except ArgParseError as e:
            await ctx.send(e.args[0])

    @customcom.command(name="cooldown")
    @checks.mod_or_permissions(administrator=True)
    async def cc_cooldown(
        self, ctx, command: str.lower, cooldown: int = None, *, per: str.lower = "member"
    ):
        """
        Sets, edits, or views cooldowns for a custom command

        You may set cooldowns per member, channel, or guild.
        Multiple cooldowns may be set. All cooldowns must be cooled to call the custom command.
        Example:
        [p]customcom cooldown yourcommand 30
        """
        if cooldown is None:
            try:
                cooldowns = (await self.commandobj.get(ctx.message, command))[1]
            except NotFound:
                return await ctx.send(_("That command doesn't exist."))
            if cooldowns:
                cooldown = []
                for per, rate in cooldowns.items():
                    cooldown.append(
                        _("A {} may call this command every {} seconds").format(per, rate)
                    )
                return await ctx.send("\n".join(cooldown))
            else:
                return await ctx.send(_("This command has no cooldown."))
        per = {"server": "guild", "user": "member"}.get(per, per)
        allowed = ("guild", "member", "channel")
        if per not in allowed:
            return await ctx.send(_("{} must be one of {}").format("per", ", ".join(allowed)))
        cooldown = {per: cooldown}
        try:
            await self.commandobj.edit(ctx=ctx, command=command, cooldowns=cooldown, ask_for=False)
            await ctx.send(_("Custom command cooldown successfully edited."))
        except NotFound:
            await ctx.send(
                _("That command doesn't exist. Use `{}` to add it.").format(
                    "{}customcom add".format(ctx.prefix)
                )
            )

    @customcom.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def cc_delete(self, ctx, command: str.lower):
        """Deletes a custom command

        Example:
        [p]customcom delete yourcommand"""
        try:
            await self.commandobj.delete(ctx=ctx, command=command)
            await ctx.send(_("Custom command successfully deleted."))
        except NotFound:
            await ctx.send(_("That command doesn't exist."))

    @customcom.command(name="edit")
    @checks.mod_or_permissions(administrator=True)
    async def cc_edit(self, ctx, command: str.lower, *, text: str = None):
        """Edits a custom command's response

        Example:
        [p]customcom edit yourcommand Text you want
        """
        try:
            await self.commandobj.edit(ctx=ctx, command=command, response=text)
            await ctx.send(_("Custom command successfully edited."))
        except NotFound:
            await ctx.send(
                _("That command doesn't exist. Use `{}` to add it.").format(
                    "{}customcom add".format(ctx.prefix)
                )
            )
        except ArgParseError as e:
            await ctx.send(e.args[0])

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

    # This is the only CC instance, but it is copied as needed
    @custom_command
    async def __cc_command(self, ctx, *args, **kwargs) -> None:
        """
        Custom command.

        Created via the CustomCom cog. See `[p]customcom` for more details.
        """
        raw_response = kwargs.pop("raw_response")
        args = (*args, *kwargs.values())
        results = re.findall(r"\{([^}]+)\}", raw_response)
        for result in results:
            param = self.transform_parameter(result, ctx.message)
            raw_response = raw_response.replace("{" + result + "}", param)
        results = re.findall(r"\{((\d+)[^\.}]*(\.[^:}]+)?[^}]*)\}", raw_response)
        if results:
            low = min(int(result[1]) for result in results)
            for result in results:
                index = int(result[1]) - low
                arg = self.transform_arg(result[0], result[2], args[index])
                raw_response = raw_response.replace("{" + result[0] + "}", arg)
        await ctx.send(raw_response)

    async def cc_prepare(self, ctx) -> str:
        try:
            raw_response, cooldowns = await self.commandobj.get(
                message=ctx.message, command=ctx.invoked_with
            )
            if isinstance(raw_response, list):
                raw_response = random.choice(raw_response)
            elif isinstance(raw_response, str):
                pass
            else:
                raise NotFound()
            if cooldowns:
                self.test_cooldowns(ctx, ctx.invoked_with, cooldowns)
        except CCError as e:
            raise commands.CheckFailure() from e
        ctx.command.params = self.prepare_args(raw_response)
        return raw_response

    def prepare_args(self, raw_response) -> Mapping[str, Parameter]:
        args = re.findall(r"\{(\d+)[^:}]*(:[^\.}]*)?[^}]*\}", raw_response)
        default = [
            ["self", Parameter("self", Parameter.POSITIONAL_OR_KEYWORD)],
            ["ctx", Parameter("ctx", Parameter.POSITIONAL_OR_KEYWORD)],
        ]
        if not args:
            return OrderedDict(default)
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
        indices = [int(a[0]) for a in args]
        low = min(indices)
        indices = [a - low for a in indices]
        high = max(indices)
        if high > 9:
            raise ArgParseError(_("Too many arguments!"))
        gaps = set(indices).symmetric_difference(range(high + 1))
        if gaps:
            raise ArgParseError(
                _("Arguments must be sequential. Missing arguments: {}.").format(
                    ", ".join(str(i + low) for i in gaps)
                )
            )
        fin = [Parameter("_" + str(i), Parameter.POSITIONAL_OR_KEYWORD) for i in range(high + 1)]
        for arg in args:
            index = int(arg[0]) - low
            anno = arg[1][1:]  # strip initial colon
            if anno.lower().endswith("converter"):
                anno = anno[:-9]
            if not anno or anno.startswith("_"):  # public types only
                name = "{}_{}".format("text", index if index < high else "final")
                fin[index] = fin[index].replace(name=name)
                continue
            # allow type hinting only for discord.py and builtin types
            try:
                anno = getattr(discord, anno)
                # force an AttributeError if there's no discord.py converter
                getattr(commands.converter, anno.__name__ + "Converter")
            except AttributeError:
                anno = allowed_builtins.get(anno.lower(), Parameter.empty)
            if (
                anno is not Parameter.empty
                and fin[index].annotation is not Parameter.empty
                and anno != fin[index].annotation
            ):
                raise ArgParseError(
                    _('Conflicting colon notation for argument {}: "{}" and "{}".').format(
                        index + low, fin[index].annotation.__name__, anno.__name__
                    )
                )
            if anno is not Parameter.empty:
                fin[index] = fin[index].replace(annotation=anno)
        # consume rest
        fin[-1] = fin[-1].replace(kind=Parameter.KEYWORD_ONLY)
        # name the parameters for the help text
        for i, param in enumerate(fin):
            anno = param.annotation
            name = "{}_{}".format(
                "text" if anno is Parameter.empty else anno.__name__.lower(),
                i if i < high else "final",
            )
            fin[i] = fin[i].replace(name=name)
        # insert ctx parameter for discord.py parsing
        fin = default + [(p.name, p) for p in fin]
        return OrderedDict(fin)

    def test_cooldowns(self, ctx, command, cooldowns):
        now = datetime.utcnow()
        new_cooldowns = {}
        for per, rate in cooldowns.items():
            if per == "guild":
                key = (command, ctx.guild)
            elif per == "channel":
                key = (command, ctx.guild, ctx.channel)
            elif per == "member":
                key = (command, ctx.guild, ctx.author)
            cooldown = self.cooldowns.get(key)
            if cooldown:
                cooldown += timedelta(seconds=rate)
                if cooldown > now:
                    raise OnCooldown()
            new_cooldowns[key] = now
        # only update cooldowns if the command isn't on cooldown
        self.cooldowns.update(new_cooldowns)

    def transform_arg(self, result, attr, obj) -> str:
        attr = attr[1:]  # strip initial dot
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
