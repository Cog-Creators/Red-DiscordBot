"""Overrides the built-in help formatter.

All help messages will be embed and pretty.

Most of the code stolen from
discord.ext.commands.formatter.py and
converted into embeds instead of codeblocks.

Docstr on cog class becomes category.
Docstr on command definition becomes command
summary and usage.
Use [p] in command docstr for bot prefix.

See [p]help here for example.

await bot.formatter.format_help_for(ctx, command)
to send help page for command. Optionally pass a
string as third arg to add a more descriptive
message to help page.
e.g. format_help_for(ctx, ctx.command, "Missing required arguments")

discord.py 1.0.0a
Experimental: compatibility with 0.16.8

Copyrights to logic of code belong to Rapptz (Danny)
Everything else credit to SirThane#1780"""
from collections import namedtuple
from typing import List

import discord
from discord.ext.commands import formatter
import inspect
import itertools
import re
import sys
import traceback

from . import commands


EMPTY_STRING = u"\u200b"

_mentions_transforms = {"@everyone": "@\u200beveryone", "@here": "@\u200bhere"}

_mention_pattern = re.compile("|".join(_mentions_transforms.keys()))

EmbedField = namedtuple("EmbedField", "name value inline")


class Help(formatter.HelpFormatter):
    """Formats help for commands."""

    def __init__(self, *args, **kwargs):
        self.context = None
        self.command = None
        super().__init__(*args, **kwargs)

    def pm_check(self, ctx):
        return isinstance(ctx.channel, discord.DMChannel)

    @property
    def me(self):
        return self.context.me

    @property
    def bot_all_commands(self):
        return self.context.bot.all_commands

    @property
    def avatar(self):
        return self.context.bot.user.avatar_url_as(format="png")

    @property
    def color(self):
        if self.pm_check(self.context):
            return 0
        else:
            return self.me.color

    @property
    def destination(self):
        if self.context.bot.pm_help:
            return self.context.author
        return self.context

    # All the other shit

    @property
    def author(self):
        # Get author dict with username if PM and display name in guild
        if self.pm_check(self.context):
            name = self.context.bot.user.name
        else:
            name = self.me.display_name if not "" else self.context.bot.user.name
        author = {"name": "{0} Help Manual".format(name), "icon_url": self.avatar}
        return author

    def _add_subcommands(self, cmds):
        entries = ""
        for name, command in cmds:
            if name in command.aliases:
                # skip aliases
                continue

            if self.is_cog() or self.is_bot():
                name = "{0}{1}".format(self.clean_prefix, name)

            entries += "**{0}**   {1}\n".format(name, command.short_doc)
        return entries

    def get_ending_note(self):
        # command_name = self.context.invoked_with
        return (
            "Type {0}help <command> for more info on a command.\n"
            "You can also type {0}help <category> for more info on a category.".format(
                self.clean_prefix
            )
        )

    async def format(self) -> dict:
        """Formats command for output.

        Returns a dict used to build embed"""
        emb = {"embed": {"title": "", "description": ""}, "footer": {"text": ""}, "fields": []}

        if self.is_cog():
            translator = getattr(self.command, "__translator__", lambda s: s)
            description = (
                inspect.cleandoc(translator(self.command.__doc__))
                if self.command.__doc__
                else EMPTY_STRING
            )
        else:
            description = self.command.description

        if not description == "" and description is not None:
            description = "*{0}*".format(description)

        if description:
            # <description> portion
            emb["embed"]["description"] = description[:2046]

        footer = self.get_ending_note()
        tagline = await self.context.bot.db.help.tagline()
        if tagline:
            footer += "\n\n{}".format(tagline)
        emb["footer"]["text"] = footer

        if isinstance(self.command, discord.ext.commands.core.Command):
            # <signature portion>
            emb["embed"]["title"] = emb["embed"]["description"]
            emb["embed"]["description"] = "`Syntax: {0}`".format(self.get_command_signature())

            # <long doc> section
            if self.command.help:
                splitted = self.command.help.split("\n\n")
                name = "__{0}__".format(splitted[0])
                value = "\n\n".join(splitted[1:]).replace("[p]", self.clean_prefix)
                if value == "":
                    value = EMPTY_STRING
                field = EmbedField(name[:252], value[:1024], False)
                emb["fields"].append(field)

            # end it here if it's just a regular command
            if not self.has_subcommands():
                return emb

        def category(tup):
            # Turn get cog (Category) name from cog/list tuples
            cog = tup[1].cog_name
            return "**__{0}:__**".format(cog) if cog is not None else "**__\u200bNo Category:__**"

        # Get subcommands for bot or category
        filtered = await self.filter_command_list()

        if self.is_bot():
            # Get list of non-hidden commands for bot.
            data = sorted(filtered, key=category)
            for category, commands_ in itertools.groupby(data, key=category):
                commands_ = sorted(commands_)
                if len(commands_) > 0:
                    field = EmbedField(category, self._add_subcommands(commands_), False)
                    emb["fields"].append(field)

        else:
            # Get list of commands for category
            filtered = sorted(filtered)
            if filtered:
                field = EmbedField(
                    "**__Commands:__**"
                    if not self.is_bot() and self.is_cog()
                    else "**__Subcommands:__**",
                    self._add_subcommands(filtered),  # May need paginated
                    False,
                )

                emb["fields"].append(field)

        return emb

    def group_fields(self, fields: List[EmbedField], max_chars=1000):
        curr_group = []
        ret = []
        for f in fields:
            curr_group.append(f)
            if sum(len(f.value) for f in curr_group) > max_chars:
                ret.append(curr_group)
                curr_group = []

        if len(curr_group) > 0:
            ret.append(curr_group)

        return ret

    async def format_help_for(self, ctx, command_or_bot, reason: str = None):
        """Formats the help page and handles the actual heavy lifting of how  ### WTF HAPPENED?
        the help command looks like. To change the behaviour, override the
        :meth:`~.HelpFormatter.format` method.

        Parameters
        -----------
        ctx: :class:`.Context`
            The context of the invoked help command.
        command_or_bot: :class:`.Command` or :class:`.Bot`
            The bot or command that we are getting the help of.
        reason : str

        Returns
        --------
        list
            A paginated output of the help command.
        """
        self.context = ctx
        self.command = command_or_bot
        emb = await self.format()

        if reason:
            emb["embed"]["title"] = "{0}".format(reason)

        ret = []

        page_char_limit = await ctx.bot.db.help.page_char_limit()
        field_groups = self.group_fields(emb["fields"], page_char_limit)

        for i, group in enumerate(field_groups, 1):
            embed = discord.Embed(color=self.color, **emb["embed"])

            if len(field_groups) > 1:
                description = "{} *- Page {} of {}*".format(
                    embed.description, i, len(field_groups)
                )
                embed.description = description

            embed.set_author(**self.author)

            for field in group:
                embed.add_field(**field._asdict())

            embed.set_footer(**emb["footer"])

            ret.append(embed)

        return ret

    def simple_embed(self, ctx, title=None, description=None, color=None):
        # Shortcut
        self.context = ctx
        if color is None:
            color = self.color
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=ctx.bot.formatter.get_ending_note())
        embed.set_author(**self.author)
        return embed

    def cmd_not_found(self, ctx, cmd, color=None):
        # Shortcut for a shortcut. Sue me
        embed = self.simple_embed(
            ctx,
            title=ctx.bot.command_not_found.format(cmd),
            description="Commands are case sensitive. Please check your spelling and try again",
            color=color,
        )
        return embed

    def cmd_has_no_subcommands(self, ctx, cmd, color=None):
        embed = self.simple_embed(
            ctx, title=ctx.bot.command_has_no_subcommands.format(cmd), color=color
        )
        return embed


@commands.command()
async def help(ctx, *cmds: str):
    """Shows help documentation.

    [p]**help**: Shows the help manual.
    [p]**help** command: Show help for a command
    [p]**help** Category: Show commands and description for a category"""
    destination = ctx.author if ctx.bot.pm_help else ctx

    def repl(obj):
        return _mentions_transforms.get(obj.group(0), "")

    use_embeds = await ctx.embed_requested()
    f = formatter.HelpFormatter()
    # help by itself just lists our own commands.
    if len(cmds) == 0:
        if use_embeds:
            embeds = await ctx.bot.formatter.format_help_for(ctx, ctx.bot)
        else:
            embeds = await f.format_help_for(ctx, ctx.bot)
    elif len(cmds) == 1:
        # try to see if it is a cog name
        name = _mention_pattern.sub(repl, cmds[0])
        command = None
        if name in ctx.bot.cogs:
            command = ctx.bot.cogs[name]
        else:
            command = ctx.bot.all_commands.get(name)
            if command is None:
                if use_embeds:
                    await destination.send(embed=ctx.bot.formatter.cmd_not_found(ctx, name))
                else:
                    await destination.send(ctx.bot.command_not_found.format(name))
                return
        if use_embeds:
            embeds = await ctx.bot.formatter.format_help_for(ctx, command)
        else:
            embeds = await f.format_help_for(ctx, command)
    else:
        name = _mention_pattern.sub(repl, cmds[0])
        command = ctx.bot.all_commands.get(name)
        if command is None:
            if use_embeds:
                await destination.send(embed=ctx.bot.formatter.cmd_not_found(ctx, name))
            else:
                await destination.send(ctx.bot.command_not_found.format(name))
            return

        for key in cmds[1:]:
            try:
                key = _mention_pattern.sub(repl, key)
                command = command.all_commands.get(key)
                if command is None:
                    if use_embeds:
                        await destination.send(embed=ctx.bot.formatter.cmd_not_found(ctx, key))
                    else:
                        await destination.send(ctx.bot.command_not_found.format(key))
                    return
            except AttributeError:
                if use_embeds:
                    await destination.send(
                        embed=ctx.bot.formatter.simple_embed(
                            ctx,
                            title='Command "{0.name}" has no subcommands.'.format(command),
                            color=ctx.bot.formatter.color,
                        )
                    )
                else:
                    await destination.send(ctx.bot.command_has_no_subcommands.format(command))
                return
        if use_embeds:
            embeds = await ctx.bot.formatter.format_help_for(ctx, command)
        else:
            embeds = await f.format_help_for(ctx, command)

    max_pages_in_guild = await ctx.bot.db.help.max_pages_in_guild()
    if len(embeds) > max_pages_in_guild:
        destination = ctx.author

    for embed in embeds:
        if use_embeds:
            try:
                await destination.send(embed=embed)
            except discord.HTTPException:
                destination = ctx.author
                await destination.send(embed=embed)
        else:
            try:
                await destination.send(embed)
            except discord.HTTPException:
                destination = ctx.author
                await destination.send(embed)


@help.error
async def help_error(ctx, error):
    destination = ctx.author if ctx.bot.pm_help else ctx
    await destination.send("{0.__name__}: {1}".format(type(error), error))
    traceback.print_tb(error.original.__traceback__, file=sys.stderr)
