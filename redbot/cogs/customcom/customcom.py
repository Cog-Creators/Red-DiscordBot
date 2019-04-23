import re
import random
from datetime import datetime, timedelta
from inspect import Parameter
from collections import OrderedDict
from typing import Mapping, Tuple, Dict, Set

import discord

from redbot.core import Config, checks, commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils import menus
from redbot.core.utils.chat_formatting import box, pagify, escape
from redbot.core.utils.predicates import MessagePredicate

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
        config = kwargs.get("config")
        self.bot = kwargs.get("bot")
        self.db = config.guild

    @staticmethod
    async def get_commands(config) -> dict:
        _commands = await config.commands()
        return {k: v for k, v in _commands.items() if _commands[k]}

    async def get_responses(self, ctx):
        intro = _(
            "Welcome to the interactive random {cc} maker!\n"
            "Every message you send will be added as one of the random "
            "responses to choose from once this {cc} is "
            "triggered. To exit this interactive menu, type `{quit}`"
        ).format(cc="customcommand", quit="exit()")
        await ctx.send(intro)

        responses = []
        args = None
        while True:
            await ctx.send(_("Add a random response:"))
            msg = await self.bot.wait_for("message", check=MessagePredicate.same_context(ctx))

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

    @staticmethod
    def get_now() -> str:
        # Get current time as a string, for 'created_at' and 'edited_at' fields
        # in the ccinfo dict
        return "{:%d/%m/%Y %H:%M:%S}".format(datetime.utcnow())

    async def get(self, message: discord.Message, command: str) -> Tuple[str, Dict]:
        ccinfo = await self.db(message.guild).commands.get_raw(command, default=None)
        if not ccinfo:
            raise NotFound()
        else:
            return ccinfo["response"], ccinfo.get("cooldowns", {}), ccinfo["mod"]

    async def get_full(self, message: discord.Message, command: str) -> Dict:
        ccinfo = await self.db(message.guild).commands.get_raw(command, default=None)
        if ccinfo:
            return ccinfo
        else:
            raise NotFound()

    async def create(self, ctx: commands.Context, command: str, *, response, mod: bool = False):
        """Create a custom command"""
        # Check if this command is already registered as a customcommand
        if await self.db(ctx.guild).commands.get_raw(command, default=None):
            raise AlreadyExists()
        # test to raise
        ctx.cog.prepare_args(response if isinstance(response, str) else response[0])
        author = ctx.message.author
        ccinfo = {
            "author": {"id": author.id, "name": str(author)},
            "command": command,
            "cooldowns": {},
            "created_at": self.get_now(),
            "editors": [],
            "response": response,
            "mod": mod,
        }
        await self.db(ctx.guild).commands.set_raw(command, value=ccinfo)

    async def edit(
        self,
        ctx: commands.Context,
        command: str,
        *,
        response=None,
        cooldowns: Mapping[str, int] = None,
        ask_for: bool = True,
    ):
        """Edit an already existing custom command"""
        ccinfo = await self.db(ctx.guild).commands.get_raw(command, default=None)

        # Check if this command is registered
        if not ccinfo:
            raise NotFound()

        author = ctx.message.author

        if ask_for and not response:
            await ctx.send(_("Do you want to create a 'randomized' custom command? (y/n)"))

            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=30)
            except TimeoutError:
                await ctx.send(_("Response timed out, please try again later."))
                return
            if pred.result is True:
                response = await self.get_responses(ctx=ctx)
            else:
                await ctx.send(_("What response do you want?"))
                try:
                    resp = await self.bot.wait_for(
                        "message", check=MessagePredicate.same_context(ctx), timeout=180
                    )
                except TimeoutError:
                    await ctx.send(_("Response timed out, please try again later."))
                    return
                response = resp.content

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


@cog_i18n(_)
class CustomCommands(commands.Cog):
    """Creates commands used to display text."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.key = 414589031223512
        self.config = Config.get_conf(self, self.key)
        self.config.register_guild(commands={})
        self.commandobj = CommandObj(config=self.config, bot=self.bot)
        self.cooldowns = {}

    @commands.group(aliases=["cc"])
    @commands.guild_only()
    async def customcom(self, ctx: commands.Context):
        """Custom commands management."""
        pass

    @customcom.group(name="create", aliases=["add"])
    @checks.mod_or_permissions(administrator=True)
    async def cc_create(self, ctx: commands.Context):
        """Create custom commands.

        CCs can be enhanced with arguments, see the guide
        [here](https://red-discordbot.readthedocs.io/en/v3-develop/cog_customcom.html).
        """
        pass

    @cc_create.command(name="random")
    @checks.mod_or_permissions(administrator=True)
    async def cc_create_random(self, ctx: commands.Context, command: str.lower):
        """Create a CC where it will randomly choose a response!

        Note: This command is interactive.
        """
        responses = await self.commandobj.get_responses(ctx=ctx)
        try:
            await self.commandobj.create(ctx=ctx, command=command, response=responses)
            await ctx.send(_("Custom command successfully added."))
        except AlreadyExists:
            await ctx.send(
                _("This command already exists. Use `{command}` to edit it.").format(
                    command="{}customcom edit".format(ctx.prefix)
                )
            )

    @cc_create.command(name="simple")
    @checks.mod_or_permissions(administrator=True)
    async def cc_create_simple(self, ctx, command: str.lower, *, text: str):
        """Add a simple custom command.

        Example:
        - `[p]customcom create simple yourcommand Text you want`
        """
        if command in self.bot.all_commands:
            await ctx.send(_("There already exists a bot command with the same name."))
            return
        try:
            await self.commandobj.create(ctx=ctx, command=command, response=text)
            await ctx.send(_("Custom command successfully added."))
        except AlreadyExists:
            await ctx.send(
                _("This command already exists. Use `{command}` to edit it.").format(
                    command="{}customcom edit".format(ctx.prefix)
                )
            )
        except ArgParseError as e:
            await ctx.send(e.args[0])

    @cc_create.command(name="mod")
    @checks.mod_or_permissions(administrator=True)
    async def cc_create_mod(self, ctx, command: str.lower, *, text: str):
        """Add a simple custom command, but locked to moderators only,
        that will be able to use @here and @everyone.

        Example:
        - `[p]customcom create mod wakeup @everyone wake up`
        """
        if command in self.bot.all_commands:
            await ctx.send(_("There already exists a bot command with the same name."))
            return
        try:
            await self.commandobj.create(ctx=ctx, command=command, response=text, mod=True)
            await ctx.send(_("Custom command successfully added."))
        except AlreadyExists:
            await ctx.send(
                _("This command already exists. Use `{command}` to edit it.").format(
                    command="{}customcom edit".format(ctx.prefix)
                )
            )
        except ArgParseError as e:
            await ctx.send(e.args[0])

    @customcom.command(name="cooldown")
    @checks.mod_or_permissions(administrator=True)
    async def cc_cooldown(
        self, ctx, command: str.lower, cooldown: int = None, *, per: str.lower = "member"
    ):
        """Set, edit, or view the cooldown for a custom command.

        You may set cooldowns per member, channel, or guild. Multiple
        cooldowns may be set. All cooldowns must be cooled to call the
        custom command.

        Example:
        - `[p]customcom cooldown yourcommand 30`
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
                _("That command doesn't exist. Use `{command}` to add it.").format(
                    command="{}customcom create".format(ctx.prefix)
                )
            )

    @customcom.command(name="delete")
    @checks.mod_or_permissions(administrator=True)
    async def cc_delete(self, ctx, command: str.lower):
        """Delete a custom command.

        Example:
        - `[p]customcom delete yourcommand`
        """
        try:
            await self.commandobj.delete(ctx=ctx, command=command)
            await ctx.send(_("Custom command successfully deleted."))
        except NotFound:
            await ctx.send(_("That command doesn't exist."))

    @customcom.command(name="edit")
    @checks.mod_or_permissions(administrator=True)
    async def cc_edit(self, ctx, command: str.lower, *, text: str = None):
        """Edit a custom command.

        Example:
        - `[p]customcom edit yourcommand Text you want`
        """
        try:
            await self.commandobj.edit(ctx=ctx, command=command, response=text)
            await ctx.send(_("Custom command successfully edited."))
        except NotFound:
            await ctx.send(
                _("That command doesn't exist. Use `{command}` to add it.").format(
                    command="{}customcom create".format(ctx.prefix)
                )
            )
        except ArgParseError as e:
            await ctx.send(e.args[0])

    @customcom.command(name="list")
    @checks.bot_has_permissions(add_reactions=True)
    async def cc_list(self, ctx: commands.Context):
        """List all available custom commands.

        The list displays a preview of each command's response, with
        markdown escaped and newlines replaced with spaces.
        """
        cc_dict = await CommandObj.get_commands(self.config.guild(ctx.guild))

        if not cc_dict:
            await ctx.send(
                _(
                    "There are no custom commands in this server."
                    " Use `{command}` to start adding some."
                ).format(command="{}customcom create".format(ctx.prefix))
            )
            return

        results = []
        for command, body in sorted(cc_dict.items(), key=lambda t: t[0]):
            responses = body["response"]
            if isinstance(responses, list):
                result = ", ".join(responses)
            elif isinstance(responses, str):
                result = responses
            else:
                continue
            # Cut preview to 52 characters max
            if len(result) > 52:
                result = result[:49] + "..."
            # Replace newlines with spaces
            result = result.replace("\n", " ")
            # Escape markdown and mass mentions
            result = escape(result, formatting=True, mass_mentions=True)
            results.append((f"{ctx.clean_prefix}{command}", result))

        if await ctx.embed_requested():
            # We need a space before the newline incase the CC preview ends in link (GH-2295)
            content = " \n".join(map("**{0[0]}** {0[1]}".format, results))
            pages = list(pagify(content, page_length=1024))
            embed_pages = []
            for idx, page in enumerate(pages, start=1):
                embed = discord.Embed(
                    title=_("Custom Command List"),
                    description=page,
                    colour=await ctx.embed_colour(),
                )
                embed.set_footer(text=_("Page {num}/{total}").format(num=idx, total=len(pages)))
                embed_pages.append(embed)
            await menus.menu(ctx, embed_pages, menus.DEFAULT_CONTROLS)
        else:
            content = "\n".join(map("{0[0]:<12} : {0[1]}".format, results))
            pages = list(map(box, pagify(content, page_length=2000, shorten_by=10)))
            await menus.menu(ctx, pages, menus.DEFAULT_CONTROLS)

    @customcom.command(name="show")
    async def cc_show(self, ctx, command_name: str):
        """Shows a custom command's reponses and its settings."""

        try:
            cmd = await self.commandobj.get_full(ctx.message, command_name)
        except NotFound:
            ctx.send(_("I could not not find that custom command."))
            return

        responses = cmd["response"]

        if isinstance(responses, str):
            responses = [responses]

        author = ctx.guild.get_member(cmd["author"]["id"])
        # If the author is still in the server, show their current name
        if author:
            author = "{} ({})".format(author, cmd["author"]["id"])
        else:
            author = "{} ({})".format(cmd["author"]["name"], cmd["author"]["id"])

        _type = _("Random") if len(responses) > 1 else _("Normal")

        text = _(
            "Command: {command_name}\n"
            "Author: {author}\n"
            "Created: {created_at}\n"
            "Type: {type}\n"
        ).format(
            command_name=command_name, author=author, created_at=cmd["created_at"], type=_type
        )

        cooldowns = cmd["cooldowns"]

        if cooldowns:
            cooldown_text = _("Cooldowns:\n")
            for rate, per in cooldowns.items():
                cooldown_text += _("{num} seconds per {period}\n").format(num=per, period=rate)
            text += cooldown_text

        text += _("Responses:\n")
        responses = ["- " + r for r in responses]
        text += "\n".join(responses)

        for p in pagify(text):
            await ctx.send(box(p, lang="yaml"))

    async def on_message(self, message):
        is_private = isinstance(message.channel, discord.abc.PrivateChannel)

        # user_allowed check, will be replaced with self.bot.user_allowed or
        # something similar once it's added
        user_allowed = True

        if len(message.content) < 2 or is_private or not user_allowed or message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        if ctx.prefix is None or ctx.valid:
            return

        try:
            raw_response, cooldowns, mod = await self.commandobj.get(
                message=message, command=ctx.invoked_with
            )
            if isinstance(raw_response, list):
                raw_response = random.choice(raw_response)
            elif isinstance(raw_response, str):
                pass
            else:
                raise NotFound()
            if cooldowns:
                self.test_cooldowns(ctx, ctx.invoked_with, cooldowns)
        except CCError:
            return

        # wrap the command here so it won't register with the bot
        fake_cc = commands.Command(ctx.invoked_with, self.cc_callback)
        fake_cc.params = self.prepare_args(raw_response)
        ctx.command = fake_cc

        await self.bot.invoke(ctx)
        if not ctx.command_failed:
            await self.cc_command(*ctx.args, **ctx.kwargs, raw_response=raw_response, mod=mod)

    async def cc_callback(self, *args, **kwargs) -> None:
        """
        Custom command.

        Created via the CustomCom cog. See `[p]customcom` for more details.
        """
        # fake command to take advantage of discord.py's parsing and events
        pass

    async def cc_command(
        self, ctx, *cc_args, raw_response, mod: bool = False, **cc_kwargs
    ) -> None:
        cc_args = (*cc_args, *cc_kwargs.values())
        results = re.findall(r"{([^}]+)\}", raw_response)
        for result in results:
            param = self.transform_parameter(result, ctx.message)
            raw_response = raw_response.replace("{" + result + "}", param)
        results = re.findall(r"{((\d+)[^.}]*(\.[^:}]+)?[^}]*)\}", raw_response)
        if results:
            low = min(int(result[1]) for result in results)
            for result in results:
                index = int(result[1]) - low
                arg = self.transform_arg(result[0], result[2], cc_args[index])
                raw_response = raw_response.replace("{" + result[0] + "}", arg)
        if mod:
            if (
                ctx.bot.is_mod(ctx.author)
                or ctx.bot.is_admin(ctx.author)
                or ctx.bot.is_owner(ctx.author)
            ):  # we only allow mods to use those cc create mod ccs
                await ctx.send(
                    raw_response, filter=None
                )  ## so we have a cc create mod here, we allow here and everyone
            else:
                pass  # if someone try to use the mod cc, why should the bot respond anything ?
        else:
            await ctx.send(raw_response)

    @staticmethod
    def prepare_args(raw_response) -> Mapping[str, Parameter]:
        args = re.findall(r"{(\d+)[^:}]*(:[^.}]*)?[^}]*\}", raw_response)
        default = [("ctx", Parameter("ctx", Parameter.POSITIONAL_OR_KEYWORD))]
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
                _("Arguments must be sequential. Missing arguments: ")
                + ", ".join(str(i + low) for i in gaps)
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
                getattr(commands, anno.__name__ + "Converter")
            except AttributeError:
                anno = allowed_builtins.get(anno.lower(), Parameter.empty)
            if (
                anno is not Parameter.empty
                and fin[index].annotation is not Parameter.empty
                and anno != fin[index].annotation
            ):
                raise ArgParseError(
                    _(
                        'Conflicting colon notation for argument {index}: "{name1}" and "{name2}".'
                    ).format(
                        index=index + low,
                        name1=fin[index].annotation.__name__,
                        name2=anno.__name__,
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
            else:
                raise ValueError(per)
            cooldown = self.cooldowns.get(key)
            if cooldown:
                cooldown += timedelta(seconds=rate)
                if cooldown > now:
                    raise OnCooldown()
            new_cooldowns[key] = now
        # only update cooldowns if the command isn't on cooldown
        self.cooldowns.update(new_cooldowns)

    @staticmethod
    def transform_arg(result, attr, obj) -> str:
        attr = attr[1:]  # strip initial dot
        if not attr:
            return str(obj)
        raw_result = "{" + result + "}"
        # forbid private members and nested attr lookups
        if attr.startswith("_") or "." in attr:
            return raw_result
        return str(getattr(obj, attr, raw_result))

    @staticmethod
    def transform_parameter(result, message) -> str:
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

    async def get_command_names(self, guild: discord.Guild) -> Set[str]:
        """Get all custom command names in a guild.

        Returns
        --------
        Set[str]
            A set of all custom command names.

        """
        return set(await CommandObj.get_commands(self.config.guild(guild)))
