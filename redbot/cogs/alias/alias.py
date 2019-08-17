from copy import copy
from re import findall, search
from string import Formatter
from typing import Generator, Tuple, Iterable, Optional

import discord
from discord.ext.commands.view import StringView
from redbot.core import Config, commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box

from redbot.core.bot import Red
from .alias_entry import AliasEntry
from .rpchelpers import FakeMessage

_ = Translator("Alias", __file__)


class _TrackingFormatter(Formatter):
    def __init__(self):
        super().__init__()
        self.max = -1

    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            self.max = max((key, self.max))
        return super().get_value(key, args, kwargs)


class ArgParseError(Exception):
    pass


@cog_i18n(_)
class Alias(commands.Cog):
    """Create aliases for commands.

    Aliases are alternative names shortcuts for commands. They
    can act as both a lambda (storing arguments for repeated use)
    or as simply a shortcut to saying "x y z".

    When run, aliases will accept any additional arguments
    and append them to the stored alias.
    """

    default_global_settings = {"entries": []}

    default_guild_settings = {"enabled": False, "entries": []}  # Going to be a list of dicts

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self._aliases = Config.get_conf(self, 8927348724)

        self._aliases.register_global(**self.default_global_settings)
        self._aliases.register_guild(**self.default_guild_settings)

        # RPC
        if bot:
            self.bot.register_rpc_handler(self._add_alias_rpc)
            self.bot.register_rpc_handler(self._delete_alias_rpc)
            self.bot.register_rpc_handler(self._get_aliases_rpc)

    async def unloaded_aliases(self, guild: discord.Guild) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d) for d in (await self._aliases.guild(guild).entries()))

    async def unloaded_global_aliases(self) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d) for d in (await self._aliases.entries()))

    async def loaded_aliases(self, guild: discord.Guild) -> Generator[AliasEntry, None, None]:
        return (
            AliasEntry.from_json(d, bot=self.bot)
            for d in (await self._aliases.guild(guild).entries())
        )

    async def loaded_global_aliases(self) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d, bot=self.bot) for d in (await self._aliases.entries()))

    async def is_alias(
        self,
        guild: Optional[discord.Guild],
        alias_name: str,
        server_aliases: Iterable[AliasEntry] = (),
    ) -> Tuple[bool, Optional[AliasEntry]]:

        if not server_aliases and guild is not None:
            server_aliases = await self.unloaded_aliases(guild)

        global_aliases = await self.unloaded_global_aliases()

        for aliases in (server_aliases, global_aliases):
            for alias in aliases:
                if alias.name == alias_name:
                    return True, alias

        return False, None

    def is_command(self, alias_name: str) -> bool:
        command = self.bot.get_command(alias_name)
        return command is not None

    @staticmethod
    def is_valid_alias_name(alias_name: str) -> bool:
        return not bool(search(r"\s", alias_name)) and alias_name.isprintable()

    async def add_alias(
        self, author: discord.User, alias_name: str, command: str, global_: bool = False
    ) -> AliasEntry:
        indices = findall(r"{(\d*)}", command)
        if indices:
            try:
                indices = [int(a[0]) for a in indices]
            except IndexError:
                return False, _("Arguments must be specified with a number.")
            low = min(indices)
            indices = [a - low for a in indices]
            high = max(indices)
            gaps = set(indices).symmetric_difference(range(high + 1))
            if gaps:
                return (
                    None,
                    _("Arguments must be sequential. Missing arguments: ")
                    + ", ".join(str(i + low) for i in gaps),
                )
            command = command.format(*(f"{{{i}}}" for i in range(-low, high + low + 1)))

        alias = AliasEntry(alias_name, command, author, global_=global_)

        if global_:
            settings = self._aliases
        else:
            settings = self._aliases.guild(author.guild)
            await settings.enabled.set(True)
        async with settings.entries() as curr_aliases:
            curr_aliases.append(alias.to_json())

        return [alias]

    async def delete_alias(
        self, alias_name: str, global_: bool = False, guild: discord.Guild = None
    ) -> bool:
        if global_:
            settings = self._aliases
        else:
            settings = self._aliases.guild(guild)

        async with settings.entries() as aliases:
            for alias in aliases:
                alias_obj = AliasEntry.from_json(alias)
                if alias_obj.name == alias_name:
                    aliases.remove(alias)
                    return True

        return False

    async def get_prefix(self, message: discord.Message) -> str:
        """
        Tries to determine what prefix is used in a message object.
            Looks to identify from longest prefix to smallest.

            Will raise ValueError if no prefix is found.
        :param message: Message object
        :return:
        """
        content = message.content
        prefix_list = await self.bot.command_prefix(self.bot, message)
        prefixes = sorted(prefix_list, key=lambda pfx: len(pfx), reverse=True)
        for p in prefixes:
            if content.startswith(p):
                return p
        raise ValueError(_("No prefix found."))

    def get_extra_args_from_alias(
        self, message: discord.Message, prefix: str, alias: AliasEntry
    ) -> str:
        """
        When an alias is executed by a user in chat this function tries
            to get any extra arguments passed in with the call.
            Whitespace will be trimmed from both ends.
        :param message: 
        :param prefix: 
        :param alias: 
        :return: 
        """
        known_content_length = len(prefix) + len(alias.name)
        extra = message.content[known_content_length:]
        view = StringView(extra)
        view.skip_ws()
        extra = []
        while not view.eof:
            prev = view.index
            word = view.get_quoted_word()
            if len(word) < view.index - prev:
                word = "".join((view.buffer[prev], word, view.buffer[view.index - 1]))
            extra.append(word)
            view.skip_ws()
        return extra

    async def maybe_call_alias(
        self, message: discord.Message, aliases: Iterable[AliasEntry] = None
    ):
        try:
            prefix = await self.get_prefix(message)
        except ValueError:
            return

        try:
            potential_alias = message.content[len(prefix) :].split(" ")[0]
        except IndexError:
            return False

        is_alias, alias = await self.is_alias(
            message.guild, potential_alias, server_aliases=aliases
        )

        if is_alias:
            await self.call_alias(message, prefix, alias)

    async def call_alias(self, message: discord.Message, prefix: str, alias: AliasEntry):
        new_message = copy(message)
        try:
            args = self.get_extra_args_from_alias(message, prefix, alias)
        except commands.BadArgument as bae:
            return

        trackform = _TrackingFormatter()
        command = trackform.format(alias.command, *args)

        # noinspection PyDunderSlots
        new_message.content = "{}{} {}".format(
            prefix, command, " ".join(args[trackform.max + 1 :])
        )
        await self.bot.process_commands(new_message)

    async def check_if_valid(self, guild, alias_name):
        is_command = self.is_command(alias_name)
        if is_command:
            return _(
                "You attempted to create a new alias"
                " with the name {name} but that"
                " name is already a command on this bot."
            ).format(name=alias_name)

        is_alias, something_useless = await self.is_alias(guild, alias_name)
        if is_alias:
            return _(
                "You attempted to create a new alias"
                " with the name {name} but that"
                " alias already exists on this server."
            ).format(name=alias_name)

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            return _(
                "You attempted to create a new alias"
                " with the name {name} but that"
                " name is an invalid alias name. Alias"
                " names may not contain spaces."
            ).format(name=alias_name)
        return False

    # RPC Functions
    async def _add_alias_rpc(
        self, author_id: int, guild_id: int, alias_name: str, command: str, global_: bool = False
    ):
        """Adds an alias to the bot, can be either global or guild-wide.

        A guild ID still must be passed even if it is not global.
        Paramaters
        ----------
        author_id: int
            The ID of the author creating it.
        guild_id: int
            The ID of the guild where the alias is supposed to be being made.
        alias_name: str
            The alias that will be used.
        command: str
            The command that the alias will run.
        global_: bool
            Whether or not the alias should be global.  Defaults to False

        Returns
        ----------
        Optional[alias]
            Indicates success.  This paramater will be None if an error occurred when making the alias, otherwise it will be the JSON form of the new alias.
        Optional[str]
            A message describing what error occurred.  This is None if no error occured.
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None, "Invalid guild."
        author = guild.get_member(author_id)
        if not author:
            return None, "Invalid author."
        author.guild = guild
        invalid = await self.check_if_valid(author.guild, alias_name)
        if invalid:
            return None, invalid
        data = await self.add_alias(author, alias_name, command, global_)
        if len(data) == 1:
            return data[0].to_json(), None
        else:
            return None, data[1]

    async def _delete_alias_rpc(
        self, alias_name: str, global_: bool = False, guild_id: int = None
    ) -> bool:
        """Deletes an alias from the bot, whether in a guild or globally.

        Paramaters
        ----------
        alias_name: str
            The alias to be deleted.
        global_: bool
            Whether the alias is global or not
        guild_id: int
            The guild to delete it from.  Don't specify this if you are deleting it globally.

        Returns
        ----------
        Optional[bool]:
            Indicates success.  None if it couldn't find the guild specified or improper paramaters, False if it failed removing the alias (most likely doesn't exist), True if succeeded.
        """
        if global_ and guild_id:
            return None
        if not global_ and not guild_id:
            return None
        if not global_:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return None
        else:
            guild = None
        return await self.delete_alias(alias_name, global_, guild)

    async def _get_aliases_rpc(self, global_: bool = False, guild_id: int = None):
        """Gets the aliases globally or of a specific guild

        Paramaters
        ----------
        global_: bool
            Whether to fetch global aliases or to get guild-specific aliases.
        guild_id: bool
            Guild to get the aliases from.  This can be left empty if you are getting global alises.

        Returns
        ----------
        Optional[list]:
            List of aliases globally or for the guild you specified according to arguments, or None if improper arguments were passed or if the guild could not be found.
        """
        if not global_:
            if not guild_id:
                return None
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return None
            return [a.name for a in (await self.unloaded_aliases(guild))]
        else:
            return [a.name for a in await self.unloaded_global_aliases()]

    @commands.group()
    @commands.guild_only()
    async def alias(self, ctx: commands.Context):
        """Manage command aliases."""
        pass

    @alias.group(name="global")
    async def global_(self, ctx: commands.Context):
        """Manage global aliases."""
        pass

    @checks.mod_or_permissions(manage_guild=True)
    @alias.command(name="add")
    @commands.guild_only()
    async def _add_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Add an alias for a command."""
        invalid = await self.check_if_valid(ctx.guild, alias_name)
        if invalid:
            await ctx.send(invalid)
            return
        try:
            await self.add_alias(ctx.author, alias_name, command)
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

        await ctx.send(
            _("A new alias with the trigger `{name}` has been created.").format(name=alias_name)
        )

    @checks.is_owner()
    @global_.command(name="add")
    async def _add_global_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """Add a global alias for a command."""
        # region Alias Add Validity Checking
        invalid = await self.check_if_valid(ctx.guild, alias_name)
        if invalid:
            await ctx.send(invalid)
            return
        try:
            await self.add_alias(ctx.author, alias_name, command, global_=True)
        except ArgParseError as e:
            return await ctx.send(" ".join(e.args))

        await ctx.send(
            _("A new global alias with the trigger `{name}` has been created.").format(
                name=alias_name
            )
        )

    @alias.command(name="help")
    @commands.guild_only()
    async def _help_alias(self, ctx: commands.Context, alias_name: str):
        """Try to execute help for the base command of the alias."""
        is_alias, alias = await self.is_alias(ctx.guild, alias_name=alias_name)
        if is_alias:
            if self.is_command(alias.command):
                base_cmd = alias.command
            else:
                base_cmd = alias.command.rsplit(" ", 1)[0]

            new_msg = copy(ctx.message)
            new_msg.content = _("{prefix}help {command}").format(
                prefix=ctx.prefix, command=base_cmd
            )
            await self.bot.process_commands(new_msg)
        else:
            await ctx.send(_("No such alias exists."))

    @alias.command(name="show")
    @commands.guild_only()
    async def _show_alias(self, ctx: commands.Context, alias_name: str):
        """Show what command the alias executes."""
        is_alias, alias = await self.is_alias(ctx.guild, alias_name)

        if is_alias:
            await ctx.send(
                _("The `{alias_name}` alias will execute the command `{command}`").format(
                    alias_name=alias_name, command=alias.command
                )
            )
        else:
            await ctx.send(_("There is no alias with the name `{name}`").format(name=alias_name))

    @checks.mod_or_permissions(manage_guild=True)
    @alias.command(name="delete", aliases=["del", "remove"])
    @commands.guild_only()
    async def _del_alias(self, ctx: commands.Context, alias_name: str):
        """Delete an existing alias on this server."""
        aliases = await self.unloaded_aliases(ctx.guild)
        try:
            next(aliases)
        except StopIteration:
            await ctx.send(_("There are no aliases on this server."))
            return

        if await self.delete_alias(alias_name, guild=ctx.guild):
            await ctx.send(
                _("Alias with the name `{name}` was successfully deleted.").format(name=alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{name}` was not found.").format(name=alias_name))

    @checks.is_owner()
    @global_.command(name="delete", aliases=["del", "remove"])
    async def _del_global_alias(self, ctx: commands.Context, alias_name: str):
        """Delete an existing global alias."""
        aliases = await self.unloaded_global_aliases()
        try:
            next(aliases)
        except StopIteration:
            await ctx.send(_("There are no aliases on this bot."))
            return

        if await self.delete_alias(alias_name, global_=True):
            await ctx.send(
                _("Alias with the name `{name}` was successfully deleted.").format(name=alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{name}` was not found.").format(name=alias_name))

    @alias.command(name="list")
    @commands.guild_only()
    async def _list_alias(self, ctx: commands.Context):
        """List the available aliases on this server."""
        names = [_("Aliases:")] + sorted(
            ["+ " + a.name for a in (await self.unloaded_aliases(ctx.guild))]
        )
        if len(names) == 0:
            await ctx.send(_("There are no aliases on this server."))
        else:
            await ctx.send(box("\n".join(names), "diff"))

    @global_.command(name="list")
    async def _list_global_alias(self, ctx: commands.Context):
        """List the available global aliases on this bot."""
        names = [_("Aliases:")] + sorted(
            ["+ " + a.name for a in await self.unloaded_global_aliases()]
        )
        if len(names) == 0:
            await ctx.send(_("There are no aliases on this server."))
        else:
            await ctx.send(box("\n".join(names), "diff"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        aliases = list(await self.unloaded_global_aliases())
        if message.guild is not None:
            aliases = aliases + list(await self.unloaded_aliases(message.guild))

        if len(aliases) == 0:
            return

        await self.maybe_call_alias(message, aliases=aliases)
