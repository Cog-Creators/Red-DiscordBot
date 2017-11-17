import asyncio
import re

import discord
from discord.ext import commands

from redbot.core import checks
from redbot.core.i18n import CogI18n
from redbot.cogs.mod.log import log
from redbot.core.context import RedContext

_ = CogI18n("Cleanup", __file__)


class Cleanup:
    """Commands for cleaning messages"""

    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def cleanup(self, ctx: RedContext):
        """Deletes messages."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @cleanup.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def text(self, ctx: commands.Context, text: str, number: int):
        """Deletes last X messages matching the specified text.

        Example:
        cleanup text \"test\" 5

        Remember to use double quotes."""

        channel = ctx.channel
        author = ctx.author

        def check(m):
            if text in m.content:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = await channel.purge(limit=number+1, check=check)
        reason = "{}({}) deleted {} messages "\
                 " containing '{}' in channel {}".format(author.name,
                                                         author.id, len(to_delete), text, channel.id)
        log.info(reason)

    @cleanup.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def user(self, ctx: commands.Context, user: discord.Member or int, number: int):
        """Deletes last X messages from specified user.

        Examples:
        cleanup user @\u200bTwentysix 2
        cleanup user Red 6"""

        channel = ctx.channel
        author = ctx.author

        def check(m):
            if isinstance(user, discord.Member) and m.author == user:
                return True
            elif m.author.id == user:  # Allow finding messages based on an ID
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = await channel.purge(limit=number, check=check)
        reason = "{}({}) deleted {} messages "\
                 " made by {}({}) in channel {}"\
                 "".format(author.name, author.id, len(to_delete),
                           user.name, user.id, channel.name)
        log.info(reason)

    @cleanup.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def after(self, ctx: commands.Context, message_id: int):
        """Deletes all messages after specified message

        To get a message id, enable developer mode in Discord's
        settings, 'appearance' tab. Then right click a message
        and copy its id.

        This command only works on bots running as bot accounts.
        """

        channel = ctx.channel
        author = ctx.author
        is_bot = ctx.bot.user.bot

        if not is_bot:
            await ctx.send(_("This command can only be used on bots with "
                             "bot accounts."))
            return

        after = await channel.get_message(message_id)

        if not after:
            await ctx.send(_("Message not found."))
            return

        to_delete = await channel.purge(limit=None, after=after)

        reason = "{}({}) deleted {} messages in channel {}"\
                 "".format(author.name, author.id,
                           len(to_delete), channel.name)
        log.info(reason)

    @cleanup.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def messages(self, ctx: commands.Context, number: int):
        """Deletes last X messages.

        Example:
        cleanup messages 26"""

        channel = ctx.channel
        author = ctx.author

        to_delete = await channel.purge(limit=number+1)
        reason = "{}({}) deleted {} messages in channel {}"\
                 "".format(author.name, author.id,
                           len(to_delete), channel.name)
        log.info(reason)

    @cleanup.command(name='bot')
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def cleanup_bot(self, ctx: commands.Context, number: int):
        """Cleans up command messages and messages from the bot"""

        channel = ctx.message.channel
        author = ctx.message.author
        is_bot = ctx.bot.user.bot

        prefixes = ctx.bot.command_prefix
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        elif callable(prefixes):
            if asyncio.iscoroutine(prefixes):
                await ctx.send(_('Coroutine prefixes not yet implemented.'))
                return
            prefixes = prefixes(ctx.bot, ctx.message)

        # In case some idiot sets a null prefix
        if '' in prefixes:
            prefixes.remove('')

        def check(m):
            if m.author.id == ctx.bot.user.id:
                return True
            elif m == ctx.message:
                return True
            p = discord.utils.find(m.content.startswith, prefixes)
            if p and len(p) > 0:
                return m.content[len(p):].startswith(tuple(ctx.bot.commands))
            return False

        to_delete = await channel.purge(limit=number+1, check=check)

        reason = "{}({}) deleted {} "\
                 " command messages in channel {}"\
                 "".format(author.name, author.id, len(to_delete),
                           channel.name)
        log.info(reason)

    @cleanup.command(name='self')
    async def cleanup_self(self, ctx: commands.Context, number: int, match_pattern: str = None):
        """Cleans up messages owned by the bot.

        By default, all messages are cleaned. If a third argument is specified,
        it is used for pattern matching: If it begins with r( and ends with ),
        then it is interpreted as a regex, and messages that match it are
        deleted. Otherwise, it is used in a simple substring test.

        Some helpful regex flags to include in your pattern:
        Dots match newlines: (?s); Ignore case: (?i); Both: (?si)
        """
        channel = ctx.channel
        author = ctx.message.author

        use_re = (match_pattern and match_pattern.startswith('r(') and
                  match_pattern.endswith(')'))

        if use_re:
            match_pattern = match_pattern[1:]  # strip 'r'
            match_re = re.compile(match_pattern)

            def content_match(c):
                return bool(match_re.match(c))
        elif match_pattern:
            def content_match(c):
                return match_pattern in c
        else:
            def content_match(_):
                return True

        def check(m):
            if m.author.id != ctx.bot.user.id:
                return False
            elif content_match(m.content):
                return True
            return False

        to_delete = await channel.purge(limit=number, check=check)

        if channel.name:
            channel_name = 'channel ' + channel.name
        else:
            channel_name = str(channel)

        reason = "{}({}) deleted {} messages "\
                 "sent by the bot in {}"\
                 "".format(author.name, author.id, len(to_delete),
                           channel_name)
        log.info(reason)
