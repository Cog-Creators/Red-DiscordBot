import discord
from copy import copy
from discord.ext import commands

from typing import Generator, Collection, Iterable
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

    default_guild_settings = {
        "enabled": False,
        "entries": []  # Going to be a list of dicts
    }

    def __init__(self, bot: Red):
        self.bot = bot
        self.file_path = "data/alias/aliases.json"
        self._aliases = Config.get_conf(self.__class__.__name__, 8927348724)
        self._aliases.register_guild(**self.default_guild_settings)

    def unloaded_aliases(self, guild: discord.Guild) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d) for d in self._aliases.guild(guild).entries())

    def loaded_aliases(self, guild: discord.Guild) -> Generator[AliasEntry, None, None]:
        return (AliasEntry.from_json(d, bot=self.bot)
                for d in self._aliases.guild(guild).entries())

    def is_alias(self, guild: discord.Guild, alias_name: str,
                 aliases: Iterable[AliasEntry]=()) -> (bool, AliasEntry):
        if aliases:
            aliases = self.unloaded_aliases(guild)

        for alias in aliases:
            if alias.name == alias_name:
                return True, alias
        return False, None

    def is_command(self, alias_name: str) -> bool:
        command = self.bot.get_command(alias_name)
        return command is not None

    def is_valid_alias_name(self, alias_name: str) -> bool:
        return alias_name.isidentifier()

    def add_alias(self, ctx: commands.Context, alias_name: str,
                  command: Collection[str]) -> AliasEntry:
        alias = AliasEntry(alias_name, command, ctx.author)
        curr_aliases = self._aliases.guild(ctx.guild).entries()

        curr_aliases.append(alias.to_json())
        self._aliases.guild(ctx.guild).set("entries", curr_aliases)

        self._aliases.guild(ctx.guild).set("enabled", True)

        return alias

    def delete_alias(self, ctx: commands.Context, alias_name: str) -> bool:
        aliases = self.unloaded_aliases(ctx.guild)
        did_delete_alias = False

        to_keep = []
        for alias in aliases:
            if alias.name != alias_name:
                to_keep.append(alias)
            else:
                did_delete_alias = True

        self._aliases.guild(ctx.guild).set(
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

        is_alias, alias = self.is_alias(message.guild, potential_alias, aliases=aliases)

        if is_alias:
            await self.call_alias(message, prefix, alias)

    async def call_alias(self, message: discord.Message, prefix: str,
                         alias: AliasEntry):
        new_message = copy(message)
        args = self.get_extra_args_from_alias(message, prefix, alias)

        # noinspection PyDunderSlots
        new_message.content = f"{prefix}{alias.command} {args}"
        await self.bot.process_commands(new_message)

    @commands.group(no_pm=True)
    async def alias(self, ctx: commands.Context):
        """Manage per-server aliases for commands"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @alias.command(name="add", no_pm=True)
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
            await ctx.send("You attempted to create a new alias"
                           f" with the name {alias_name} but that"
                           " name is already a command on this bot.")
            return

        is_alias, _ = self.is_alias(ctx.guild, alias_name)
        if is_alias:
            await ctx.send("You attempted to create a new alias"
                           f" with the name {alias_name} but that"
                           " alias already exists on this server.")
            return

        is_valid_name = self.is_valid_alias_name(alias_name)
        if not is_valid_name:
            await ctx.send("You attempted to create a new alias"
                           f" with the name {alias_name} but that"
                           " name is an invalid alias name. Alias"
                           " names may only contain letters, numbers,"
                           " and underscores and must start with a letter.")
            return
#endregion

        # At this point we know we need to make a new alias
        #   and that the alias name is valid.

        self.add_alias(ctx, alias_name, command)

        await ctx.send(f"A new alias with the trigger `{alias_name}`"
                       " has been created.")

    @alias.command(name="help", no_pm=True)
    async def _help_alias(self, ctx: commands.Context, alias_name: str):
        """Tries to execute help for the base command of the alias"""
        # TODO: attempt to show the help of the base command of the alias

    @alias.command(name="show", no_pm=True)
    async def _show_alias(self, ctx: commands.Context, alias_name: str):
        """Shows what command the alias executes."""
        # TODO: Show what command the alias executes

    @alias.command(name="del", no_pm=True)
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

        if self.delete_alias(ctx, alias_name):
            await ctx.send(f"Alias with the name `{alias_name}` was successfully"
                           " deleted.")
        else:
            await ctx.send(f"Alias with name `{alias_name}` was not found.")

    @alias.command(name="list", no_pm=True)
    async def _alias_list(self, ctx: commands.Context):
        """
        Lists the available aliases on this server.
        """
        # TODO: box this stuff
        names = ["Aliases:", ] + sorted([f"+ {a.name}" for a in self.unloaded_aliases(ctx.guild)])
        if len(names) == 0:
            await ctx.send("There are no aliases on this server.")
        else:
            await ctx.send(box("\n".join(names), "diff"))

    async def on_message(self, message: discord.Message):
        if not self._aliases.guild(message.guild).enabled():
            return

        aliases = list(self.unloaded_aliases(message.guild))

        if len(aliases) == 0:
            return

        await self.maybe_call_alias(message, aliases=aliases)
