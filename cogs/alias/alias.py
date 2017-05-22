import discord
from discord.ext import commands

from typing import Generator, Collection
from core import Config
from core.bot import Red
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

    def unloaded_aliases(self, guild: discord.Guild) -> Generator[AliasEntry]:
        return (AliasEntry.from_json(d) for d in self._aliases.guild(guild).aliases())

    def is_alias(self, guild: discord.Guild, alias_name: str) -> bool:
        for alias in self.unloaded_aliases(guild):
            if alias.alias_name == alias_name:
                return True
        return False

    def is_command(self, alias_name: str) -> bool:
        command = self.bot.get_command(alias_name)
        return command is None

    def is_valid_alias_name(self, alias_name: str) -> bool:
        # TODO: check if valid variable name
        raise NotImplementedError()

    def add_alias(self, ctx: commands.Context, alias_name: str,
                  command: Collection[str]) -> AliasEntry:
        alias = AliasEntry(alias_name, command, ctx.author)
        curr_aliases = self._aliases.guild(ctx.guild).entries()

        curr_aliases.append(alias.to_json())
        self._aliases.guild(ctx.guild).set("entries", curr_aliases)

        return alias

    @commands.group(no_pm=True)
    async def alias(self, ctx: commands.Context):
        """Manage per-server aliases for commands"""
        if ctx.invoked_subcommand is None:
            # TODO: Show help
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

        is_alias = self.is_alias(ctx.guild, alias_name)
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
        """Deletes an alias"""
        # TODO: Delete existing alias

    @alias.command(name="list", no_pm=True)
    async def _alias_list(self, ctx):
        """Lists aliases available on this server

        Responds in DM"""
        # TODO: List existing aliases

    async def on_message(self, message):
        # TODO: Determine if message begins with prefix
        # TODO: Check if enabled
        # TODO: Check if first word is an alias
        pass

    def part_of_existing_command(self, alias, server):
        '''Command or alias'''
        for command in self.bot.commands:
            if alias.lower() == command.lower():
                return True
        return False

    def first_word(self, msg):
        return msg.split(" ")[0]

    def get_prefix(self, guild: discord.Guild, msg: str) -> str:
        """
        Tries to determine what prefix is used in a message string.
            Looks to identify from longest prefix to smallest.
            
            Will raise ValueError if no prefix is found.
        :param guild: 
        :param msg: Message content string
        :return: 
        """
        prefixes = sorted(self.bot.command_prefix(guild),
                          key=lambda pfx: len(pfx),
                          reverse=True)
        for p in prefixes:
            if msg.startswith(p):
                return p
        raise ValueError("No prefix found.")
