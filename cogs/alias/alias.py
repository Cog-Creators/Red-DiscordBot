import discord
from copy import copy
from discord.ext import commands

from typing import Generator, Tuple, Iterable
from core import Config
from core.bot import Red
from core.utils.chat_formatting import box
from .alias_entry import AliasEntry


class Alias:
    """
    Alias
    
    Aliases are per server shortcuts for commands. They
        can act as both a lambda (storing arguments for repeated use)
        or as simply a shortcut to saying "x y z".
    
    When run, aliases will accept any additional arguments
        and append them to the stored alias
    """

    default_global_settings = {
        "entries": []
    }

    default_guild_settings = {
        "enabled": False,
        "entries": []  # Going to be a list of dicts
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.file_path = "data/alias/aliases.json"
        self._aliases = Config.get_conf(self, 8927348724)

        self._aliases.register_global(**self.default_global_settings)
        self._aliases.register_guild(**self.default_guild_settings)

    def unloaded_aliases(self, guild: discord.Guild) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d) for d in self._aliases.guild(guild).entries())

    def unloaded_global_aliases(self) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d) for d in self._aliases.entries())

    def loaded_aliases(self, guild: discord.Guild) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d, bot=self.bot)
                for d in self._aliases.guild(guild).entries())

    def loaded_global_aliases(self) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d, bot=self.bot) for d in self._aliases.entries())

    def is_alias(self, guild: discord.Guild, alias_name: str,
                 server_aliases: Iterable[AliasEntry]=()) -> (bool, AliasEntry):

        if not server_aliases:
            server_aliases = self.unloaded_aliases(guild)

        global_aliases = self.unloaded_global_aliases()

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
        return alias_name.isidentifier()

    async def add_alias(self, ctx: commands.Context, alias_name: str,
                        command: Tuple[str], global_: bool=False) -> AliasEntry:
        alias = AliasEntry(alias_name, command, ctx.author, global_=global_)

        if global_:
            curr_aliases = self._aliases.entries()
            curr_aliases.append(alias.to_json())
            await self._aliases.set("entries", curr_aliases)
        else:
            curr_aliases = self._aliases.guild(ctx.guild).entries()

            curr_aliases.append(alias.to_json())
            await self._aliases.guild(ctx.guild).set("entries", curr_aliases)

            await self._aliases.guild(ctx.guild).set("enabled", True)
        return alias

    async def delete_alias(self, ctx: commands.Context, alias_name: str,
                           global_: bool=False) -> bool:
        if global_:
            aliases = self.unloaded_global_aliases()
            setter_func = self._aliases.set
        else:
            aliases = self.unloaded_aliases(ctx.guild)
            setter_func = self._aliases.guild(ctx.guild).set

        did_delete_alias = False

        to_keep = []
        for alias in aliases:
            if alias.name != alias_name:
                to_keep.append(alias)
            else:
                did_delete_alias = True

        await setter_func(
            "entries",
            [a.to_json() for a in to_keep]
        )

        return did_delete_alias

    def get_prefix(self, message: discord.Message) -> str:
        """
        Tries to determine what prefix is used in a message object.
            Looks to identify from longest prefix to smallest.

            Will raise ValueError if no prefix is found.
        :param message: Message object
        :return: 
        """
        guild = message.guild
        content = message.content
        prefixes = sorted(self.bot.command_prefix(self.bot, message),
                          key=lambda pfx: len(pfx),
                          reverse=True)
        for p in prefixes:
            if content.startswith(p):
                return p
        raise ValueError("No prefix found.")

    def get_extra_args_from_alias(self, message: discord.Message, prefix: str,
                                  alias: AliasEntry) -> str:
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

    async def maybe_call_alias(self, message: discord.Message,
                               aliases: Iterable[AliasEntry]=None):
        try:
            prefix = self.get_prefix(message)
        except ValueError:
            return

        try:
            potential_alias = message.content[len(prefix):].split(" ")[0]
        except IndexError:
            return False

        is_alias, alias = self.is_alias(message.guild, potential_alias, server_aliases=aliases)

        if is_alias:
            await self.call_alias(message, prefix, alias)

    async def call_alias(self, message: discord.Message, prefix: str,
                         alias: AliasEntry):
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
            await self.bot.send_cmd_help(ctx)

    @alias.group(name="global")
    async def global_(self, ctx: commands.Context):
        """
        Manage global aliases.
        """
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await self.bot.send_cmd_help(ctx)

    @alias.command(name="add")
    @commands.guild_only()
    async def _add_alias(self, ctx: commands.Context,
                         alias_name: str, *, command):
        """
        Add an alias for a command.
        :param alias_name: 
        :param command: 
        """
#region Alias Add Validity Checking
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(("You attempted to create a new alias"
                            " with the name {} but that"
                            " name is already a command on this bot.").format(alias_name))
            return

        is_alias, _ = self.is_alias(ctx.guild, alias_name)
        if is_alias:
            await ctx.send(("You attempted to create a new alias"
                            " with the name {} but that"
                            " alias already exists on this server.").format(alias_name))
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(("You attempted to create a new alias"
                            " with the name {} but that"
                            " name is an invalid alias name. Alias"
                            " names may only contain letters, numbers,"
                            " and underscores and must start with a letter.").format(alias_name))
            return
#endregion

        # At this point we know we need to make a new alias
        #   and that the alias name is valid.

        await self.add_alias(ctx, alias_name, command)

        await ctx.send(("A new alias with the trigger `{}`"
                        " has been created.").format(alias_name))

    @global_.command(name="add")
    async def _add_global_alias(self, ctx: commands.Context,
                                alias_name: str, *, command):
        """
        Add a global alias for a command.
        :param alias_name: 
        :param command: 
        """
# region Alias Add Validity Checking
        is_command = self.is_command(alias_name)
        if is_command:
            await ctx.send(("You attempted to create a new global alias"
                            " with the name {} but that"
                            " name is already a command on this bot.").format(alias_name))
            return

        is_alias, _ = self.is_alias(ctx.guild, alias_name)
        if is_alias:
            await ctx.send(("You attempted to create a new alias"
                            " with the name {} but that"
                            " alias already exists on this server.").format(alias_name))
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send(("You attempted to create a new alias"
                            " with the name {} but that"
                            " name is an invalid alias name. Alias"
                            " names may only contain letters, numbers,"
                            " and underscores and must start with a letter.").format(alias_name))
            return
# endregion

        await self.add_alias(ctx, alias_name, command, global_=True)

        await ctx.send(("A new global alias with the trigger `{}`"
                        " has been created.").format(alias_name))

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
            ctx.send("No such alias exists.")

    @alias.command(name="show")
    @commands.guild_only()
    async def _show_alias(self, ctx: commands.Context, alias_name: str):
        """Shows what command the alias executes."""
        is_alias, alias = self.is_alias(ctx.guild, alias_name)

        if is_alias:
            await ctx.send(("The `{}` alias will execute the"
                            " command `{}`").format(alias_name, alias.command))
        else:
            await ctx.send("There is no alias with the name `{}`".format(alias_name))

    @alias.command(name="del")
    @commands.guild_only()
    async def _del_alias(self, ctx: commands.Context, alias_name: str):
        """
        Deletes an existing alias on this server.
        :param alias_name: 
        """
        aliases = self.unloaded_aliases(ctx.guild)
        try:
            next(aliases)
        except StopIteration:
            await ctx.send("There are no aliases on this guild.")

        if await self.delete_alias(ctx, alias_name):
            await ctx.send(("Alias with the name `{}` was successfully"
                            " deleted.").format(alias_name))
        else:
            await ctx.send("Alias with name `{}` was not found.".format(alias_name))

    @global_.command(name="del")
    async def _del_global_alias(self, ctx: commands.Context, alias_name: str):
        """
        Deletes an existing global alias.
        :param alias_name: 
        """
        aliases = self.unloaded_global_aliases()
        try:
            next(aliases)
        except StopIteration:
            await ctx.send("There are no aliases on this bot.")

        if await self.delete_alias(ctx, alias_name, global_=True):
            await ctx.send(("Alias with the name `{}` was successfully"
                            " deleted.").format(alias_name))
        else:
            await ctx.send("Alias with name `{}` was not found.".format(alias_name))

    @alias.command(name="list")
    @commands.guild_only()
    async def _list_alias(self, ctx: commands.Context):
        """
        Lists the available aliases on this server.
        """
        names = ["Aliases:", ] + sorted(["+ " + a.name for a in self.unloaded_aliases(ctx.guild)])
        if len(names) == 0:
            await ctx.send("There are no aliases on this server.")
        else:
            await ctx.send(box("\n".join(names), "diff"))

    @global_.command(name="list")
    async def _list_global_alias(self, ctx: commands.Context):
        """
        Lists the available global aliases on this bot.
        """
        names = ["Aliases:", ] + sorted(["+ " + a.name for a in self.unloaded_global_aliases()])
        if len(names) == 0:
            await ctx.send("There are no aliases on this server.")
        else:
            await ctx.send(box("\n".join(names), "diff"))

    async def on_message(self, message: discord.Message):
        aliases = list(self.unloaded_aliases(message.guild)) + \
            list(self.unloaded_global_aliases())

        if len(aliases) == 0:
            return

        await self.maybe_call_alias(message, aliases=aliases)
