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

This help formatter contains work by Rapptz (Danny) and SirThane#1780.
"""
import contextlib
from collections import namedtuple
from typing import List, Optional, Union

import discord
from discord.ext.commands import formatter as dpy_formatter
import inspect
import itertools
import re

from . import commands
from .i18n import Translator
from .utils.chat_formatting import pagify
from .utils import fuzzy_command_search, format_fuzzy_results

_ = Translator("Help", __file__)

EMPTY_STRING = "\u200b"

_mentions_transforms = {"@everyone": "@\u200beveryone", "@here": "@\u200bhere"}

_mention_pattern = re.compile("|".join(_mentions_transforms.keys()))

EmbedField = namedtuple("EmbedField", "name value inline")


class Help(dpy_formatter.HelpFormatter):
    """Formats help for commands."""

    def __init__(self, *args, **kwargs):
        self.context = None
        self.command = None
        super().__init__(*args, **kwargs)

    @staticmethod
    def pm_check(ctx):
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

    async def color(self):
        if self.pm_check(self.context):
            return self.context.bot.color
        else:
            return await self.context.embed_colour()

    colour = color

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
                name = "{0}{1}".format(self.context.clean_prefix, name)

            entries += "**{0}**   {1}\n".format(name, command.short_doc)
        return entries

    def get_ending_note(self):
        # command_name = self.context.invoked_with
        return (
            "Type {0}help <command> for more info on a command. "
            "You can also type {0}help <category> for more info on a category.".format(
                self.context.clean_prefix
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

        tagline = await self.context.bot.db.help.tagline()
        if tagline:
            footer = tagline
        else:
            footer = self.get_ending_note()
        emb["footer"]["text"] = footer

        if isinstance(self.command, discord.ext.commands.core.Command):
            # <signature portion>
            emb["embed"]["title"] = emb["embed"]["description"]
            emb["embed"]["description"] = "`Syntax: {0}`".format(self.get_command_signature())

            # <long doc> section
            if self.command.help:
                splitted = self.command.help.split("\n\n")
                name = "__{0}__".format(splitted[0])
                value = "\n\n".join(splitted[1:]).replace("[p]", self.context.clean_prefix)
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
                    for i, page in enumerate(
                        pagify(self._add_subcommands(commands_), page_length=1000)
                    ):
                        title = category if i < 1 else f"{category} (continued)"
                        field = EmbedField(title, page, False)
                        emb["fields"].append(field)

        else:
            # Get list of commands for category
            filtered = sorted(filtered)
            if filtered:
                for i, page in enumerate(
                    pagify(self._add_subcommands(filtered), page_length=1000)
                ):
                    title = (
                        "**__Commands:__**"
                        if not self.is_bot() and self.is_cog()
                        else "**__Subcommands:__**"
                    )
                    if i > 0:
                        title += " (continued)"
                    field = EmbedField(title, page, False)
                    emb["fields"].append(field)

        return emb

    @staticmethod
    def group_fields(fields: List[EmbedField], max_chars=1000):
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

    async def format_help_for(self, ctx, command_or_bot, reason: str = ""):
        """Formats the help page and handles the actual heavy lifting of how
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

        # We want the permission state to be set as if the author had run the command he is
        # requesting help for. This is so the subcommands shown in the help menu correctly reflect
        # any permission rules set.
        if isinstance(self.command, commands.Command):
            with contextlib.suppress(commands.CommandError):
                await self.command.can_run(
                    self.context, check_all_parents=True, change_permission_state=True
                )
        elif isinstance(self.command, commands.Cog):
            with contextlib.suppress(commands.CommandError):
                # Cog's don't have a `can_run` method, so we use the `Requires` object directly.
                await self.command.requires.verify(self.context)

        emb = await self.format()

        if reason:
            emb["embed"]["title"] = reason

        ret = []

        page_char_limit = await ctx.bot.db.help.page_char_limit()
        field_groups = self.group_fields(emb["fields"], page_char_limit)

        for i, group in enumerate(field_groups, 1):
            embed = discord.Embed(color=await self.color(), **emb["embed"])

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

    async def format_command_not_found(
        self, ctx: commands.Context, command_name: str
    ) -> Optional[Union[str, discord.Message]]:
        """Get the response for a user calling help on a missing command."""
        self.context = ctx
        return await default_command_not_found(
            ctx,
            command_name,
            use_embeds=True,
            colour=await self.colour(),
            author=self.author,
            footer={"text": self.get_ending_note()},
        )


@commands.command(hidden=True)
async def help(ctx: commands.Context, *, command_name: str = ""):
    """Show help documentation.

    - `[p]help`: Show the help manual.
    - `[p]help command`: Show help for a command.
    - `[p]help Category`: Show commands and description for a category,
    """
    bot = ctx.bot
    if bot.pm_help:
        destination = ctx.author
    else:
        destination = ctx.channel

    use_embeds = await ctx.embed_requested()
    if use_embeds:
        formatter = bot.formatter
    else:
        formatter = dpy_formatter.HelpFormatter()

    if not command_name:
        # help by itself just lists our own commands.
        pages = await formatter.format_help_for(ctx, bot)
    else:
        # First check if it's a cog
        command = bot.get_cog(command_name)
        if command is None:
            command = bot.get_command(command_name)
        if command is None:
            if hasattr(formatter, "format_command_not_found"):
                msg = await formatter.format_command_not_found(ctx, command_name)
            else:
                msg = await default_command_not_found(ctx, command_name, use_embeds=use_embeds)
            pages = [msg]
        else:
            pages = await formatter.format_help_for(ctx, command)

    max_pages_in_guild = await ctx.bot.db.help.max_pages_in_guild()
    if len(pages) > max_pages_in_guild:
        destination = ctx.author
    if ctx.guild and not ctx.guild.me.permissions_in(ctx.channel).send_messages:
        destination = ctx.author
    try:
        for page in pages:
            if isinstance(page, discord.Embed):
                await destination.send(embed=page)
            else:
                await destination.send(page)
    except discord.Forbidden:
        await ctx.channel.send(
            _(
                "I couldn't send the help message to you in DM. Either you blocked me or you "
                "disabled DMs in this server."
            )
        )


async def default_command_not_found(
    ctx: commands.Context, command_name: str, *, use_embeds: bool, **embed_options
) -> Optional[Union[str, discord.Embed]]:
    """Default function for formatting the response to a missing command."""
    ret = None
    cmds = command_name.split()
    prev_command = None
    for invoked in itertools.accumulate(cmds, lambda *args: " ".join(args)):
        command = ctx.bot.get_command(invoked)
        if command is None:
            if prev_command is not None and not isinstance(prev_command, commands.Group):
                ret = _("Command *{command_name}* has no subcommands.").format(
                    command_name=prev_command.qualified_name
                )
            break
        elif not await command.can_see(ctx):
            return
        prev_command = command

    if ret is None:
        fuzzy_commands = await fuzzy_command_search(ctx, command_name, min_score=75)
        if fuzzy_commands:
            ret = await format_fuzzy_results(ctx, fuzzy_commands, embed=use_embeds)
        else:
            ret = _("Command *{command_name}* not found.").format(command_name=command_name)

    if use_embeds:
        if isinstance(ret, str):
            ret = discord.Embed(title=ret)
        if "colour" in embed_options:
            ret.colour = embed_options.pop("colour")
        elif "color" in embed_options:
            ret.colour = embed_options.pop("color")

        if "author" in embed_options:
            ret.set_author(**embed_options.pop("author"))
        if "footer" in embed_options:
            ret.set_footer(**embed_options.pop("footer"))

    return ret
