from copy import copy
from re import search
from typing import Generator, Tuple, Iterable

import discord
from redbot.core import Config, commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box

from redbot.core.bot import Red
from .alias_entry import AliasEntry

_ = Translator("Alias", __file__)


@cog_i18n(_)
class Alias:
    """
    Alias
    
    Aliases are per server shortcuts for commands. They
        can act as both a lambda (storing arguments for repeated use)
        or as simply a shortcut to saying "x y z".
    
    When run, aliases will accept any additional arguments
        and append them to the stored alias
    """

    default_global_settings = {"entries": []}

    default_guild_settings = {"enabled": False, "entries": []}  # Going to be a list of dicts

    def __init__(self, bot: Red):
        self.bot = bot
        self._aliases = Config.get_conf(self, 8927348724)

        self._aliases.register_global(**self.default_global_settings)
        self._aliases.register_guild(**self.default_guild_settings)

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
        self, guild: discord.Guild, alias_name: str, server_aliases: Iterable[AliasEntry] = ()
    ) -> (bool, AliasEntry):

        if not server_aliases:
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
        self, ctx: commands.Context, alias_name: str, command: Tuple[str], global_: bool = False
    ) -> AliasEntry:
        alias = AliasEntry(alias_name, command, ctx.author, global_=global_)

        if global_:
            settings = self._aliases
        else:
            settings = self._aliases.guild(ctx.guild)
            await settings.enabled.set(True)

        async with settings.entries() as curr_aliases:
            curr_aliases.append(alias.to_json())

        return alias

    async def delete_alias(
        self, ctx: commands.Context, alias_name: str, global_: bool = False
    ) -> bool:
        if global_:
            settings = self._aliases
        else:
            settings = self._aliases.guild(ctx.guild)

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
        extra = message.content[known_content_length:].strip()
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
        args = self.get_extra_args_from_alias(message, prefix, alias)

        # noinspection PyDunderSlots
        new_message.content = "{}{} {}".format(prefix, alias.command, args)
        await self.bot.process_commands(new_message)

    @commands.group()
    @commands.guild_only()
    async def alias(self, ctx: commands.Context):
        """Manage per-server aliases for commands"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @alias.group(name="global")
    async def global_(self, ctx: commands.Context):
        """
        Manage global aliases.
        """
        if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
            await ctx.send_help()

    @checks.mod_or_permissions(manage_guild=True)
    @alias.command(name="add")
    @commands.guild_only()
    async def _add_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """
        Add an alias for a command.
        """
        # region Alias Add Validity Checking
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {} but that"
                    " name is already a command on this bot."
                ).format(alias_name)
            )
            return

        is_alias, something_useless = await self.is_alias(ctx.guild, alias_name)
        if is_alias:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {} but that"
                    " alias already exists on this server."
                ).format(alias_name)
            )
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(
                _(
                    "You attempted to create a new alias"
                    " with the name {} but that"
                    " name is an invalid alias name. Alias"
                    " names may not contain spaces."
                ).format(alias_name)
            )
            return
        # endregion

        # At this point we know we need to make a new alias
        #   and that the alias name is valid.

        await self.add_alias(ctx, alias_name, command)

        await ctx.send(
            _("A new alias with the trigger `{}`" " has been created.").format(alias_name)
        )

    @checks.is_owner()
    @global_.command(name="add")
    async def _add_global_alias(self, ctx: commands.Context, alias_name: str, *, command):
        """
        Add a global alias for a command.
        """
        # region Alias Add Validity Checking
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {} but that"
                    " name is already a command on this bot."
                ).format(alias_name)
            )
            return

        is_alias, something_useless = await self.is_alias(ctx.guild, alias_name)
        if is_alias:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {} but that"
                    " alias already exists on this server."
                ).format(alias_name)
            )
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(
                _(
                    "You attempted to create a new global alias"
                    " with the name {} but that"
                    " name is an invalid alias name. Alias"
                    " names may not contain spaces."
                ).format(alias_name)
            )
            return
        # endregion

        await self.add_alias(ctx, alias_name, command, global_=True)

        await ctx.send(
            _("A new global alias with the trigger `{}`" " has been created.").format(alias_name)
        )

    @alias.command(name="help")
    @commands.guild_only()
    async def _help_alias(self, ctx: commands.Context, alias_name: str):
        """Tries to execute help for the base command of the alias"""
        is_alias, alias = self.is_alias(ctx.guild, alias_name=alias_name)
        if is_alias:
            base_cmd = alias.command[0]

            new_msg = copy(ctx.message)
            new_msg.content = "{}help {}".format(ctx.prefix, base_cmd)
            await self.bot.process_commands(new_msg)
        else:
            ctx.send(_("No such alias exists."))

    @alias.command(name="show")
    @commands.guild_only()
    async def _show_alias(self, ctx: commands.Context, alias_name: str):
        """Shows what command the alias executes."""
        is_alias, alias = await self.is_alias(ctx.guild, alias_name)

        if is_alias:
            await ctx.send(
                _("The `{}` alias will execute the" " command `{}`").format(
                    alias_name, alias.command
                )
            )
        else:
            await ctx.send(_("There is no alias with the name `{}`").format(alias_name))

    @checks.mod_or_permissions(manage_guild=True)
    @alias.command(name="del")
    @commands.guild_only()
    async def _del_alias(self, ctx: commands.Context, alias_name: str):
        """
        Deletes an existing alias on this server.
        """
        aliases = await self.unloaded_aliases(ctx.guild)
        try:
            next(aliases)
        except StopIteration:
            await ctx.send(_("There are no aliases on this guild."))
            return

        if await self.delete_alias(ctx, alias_name):
            await ctx.send(
                _("Alias with the name `{}` was successfully" " deleted.").format(alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{}` was not found.").format(alias_name))

    @checks.is_owner()
    @global_.command(name="del")
    async def _del_global_alias(self, ctx: commands.Context, alias_name: str):
        """
        Deletes an existing global alias.
        """
        aliases = await self.unloaded_global_aliases()
        try:
            next(aliases)
        except StopIteration:
            await ctx.send(_("There are no aliases on this bot."))
            return

        if await self.delete_alias(ctx, alias_name, global_=True):
            await ctx.send(
                _("Alias with the name `{}` was successfully" " deleted.").format(alias_name)
            )
        else:
            await ctx.send(_("Alias with name `{}` was not found.").format(alias_name))

    @alias.command(name="list")
    @commands.guild_only()
    async def _list_alias(self, ctx: commands.Context):
        """
        Lists the available aliases on this server.
        """
        names = [_("Aliases:")] + sorted(
            ["+ " + a.name for a in (await self.unloaded_aliases(ctx.guild))]
        )
        if len(names) == 0:
            await ctx.send(_("There are no aliases on this server."))
        else:
            await ctx.send(box("\n".join(names), "diff"))

    @global_.command(name="list")
    async def _list_global_alias(self, ctx: commands.Context):
        """
        Lists the available global aliases on this bot.
        """
        names = [_("Aliases:")] + sorted(
            ["+ " + a.name for a in await self.unloaded_global_aliases()]
        )
        if len(names) == 0:
            await ctx.send(_("There are no aliases on this server."))
        else:
            await ctx.send(box("\n".join(names), "diff"))

    async def on_message(self, message: discord.Message):
        aliases = list(await self.unloaded_global_aliases())
        if message.guild is not None:
            aliases = aliases + list(await self.unloaded_aliases(message.guild))

        if len(aliases) == 0:
            return

        await self.maybe_call_alias(message, aliases=aliases)
