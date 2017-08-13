import asyncio
import logging
import re

import discord
from discord.ext import commands

from core import checks
from core.bot import Red
from .common import slow_deletion, mass_purge


class Cleanup:
    """Commands for cleaning messages"""

    def __init__(self, bot: Red):
        self.bot = bot
        global logger
        logger = logging.getLogger("mod")
        # Prevents the logger from being loaded again in case of module reload
        """
        if logger.level == 0:
            logger.setLevel(logging.INFO)
            handler = logging.FileHandler(
                filename='cogs/.data/Mod/mod.log', encoding='utf-8', mode='a')
            handler.setFormatter(
                logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
            logger.addHandler(handler)
        """

    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    async def cleanup(self, ctx: commands.Context):
        """Deletes messages."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

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
        is_bot = self.bot.user.bot

        def check(m):
            if text in m.content:
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = [ctx.message]

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in channel.history(limit=100,
                                                 before=tmp):
                if len(to_delete) - 1 < number and check(message) and\
                        (ctx.message.created_at - message.created_at).days < 14:
                    to_delete.append(message)
                elif (ctx.message.created_at - message.created_at).days >= 14:
                    tries_left = 0
                    break
                tmp = message
            if tries_left:
                tries_left -= 1

        reason = "{}({}) deleted {} messages "\
                 " containing '{}' in channel {}".format(author.name,
                                                         author.id, len(to_delete), text, channel.id)
        logger.info(reason)

        if is_bot:
            await mass_purge(to_delete, channel, reason)
        else:
            await slow_deletion(to_delete, reason)

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
        is_bot = self.bot.user.bot

        def check(m):
            if isinstance(user, discord.Member) and m.author == user:
                return True
            elif m.author.id == user:  # Allow finding messages based on an ID
                return True
            elif m == ctx.message:
                return True
            else:
                return False

        to_delete = []

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in channel.history(limit=100,
                                                 before=tmp):
                if len(to_delete) - 1 < number and check(message) and\
                        (ctx.message.created_at - message.created_at).days < 14:
                    to_delete.append(message)
                elif (ctx.message.created_at - message.created_at).days >= 14:
                    tries_left = 0
                tmp = message
            if tries_left:  # triggers if not already 0 (which evals to False)
                tries_left -= 1
        reason = "{}({}) deleted {} messages "\
                 " made by {}({}) in channel {}"\
                 "".format(author.name, author.id, len(to_delete),
                           user.name, user.id, channel.name)
        logger.info(reason)

        if is_bot:
            # For whatever reason the purge endpoint requires manage_messages
            await mass_purge(to_delete, channel, reason)
        else:
            await slow_deletion(to_delete, reason)

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
        is_bot = self.bot.user.bot

        if not is_bot:
            await ctx.send("This command can only be used on bots with "
                           "bot accounts.")
            return

        after = await channel.get_message(message_id)

        if not after:
            await ctx.send("Message not found.")
            return

        to_delete = []

        async for message in channel.history(after=after):
            if (ctx.message.created_at - message.created_at).days < 14:
                # Only add messages that are less than
                # 14 days old to the deletion queue
                to_delete.append(message)

        reason = "{}({}) deleted {} messages in channel {}"\
                 "".format(author.name, author.id,
                           len(to_delete), channel.name)
        logger.info(reason)

        await mass_purge(to_delete, channel, reason)

    @cleanup.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def messages(self, ctx: commands.Context, number: int):
        """Deletes last X messages.

        Example:
        cleanup messages 26"""

        channel = ctx.channel
        author = ctx.author

        is_bot = self.bot.user.bot

        to_delete = []
        tmp = ctx.message

        done = False

        while len(to_delete) - 1 < number and not done:
            async for message in channel.history(limit=100, before=tmp):
                if (ctx.message.created_at - message.created_at).days < 14:
                    to_delete.append(message)
                elif (ctx.message.created_at - message.created_at).days >= 14:
                    done = True
                    break
                tmp = message

        reason = "{}({}) deleted {} messages in channel {}"\
                 "".format(author.name, author.id,
                           number, channel.name)
        logger.info(reason)

        if is_bot:
            await mass_purge(to_delete, channel, reason)
        else:
            await slow_deletion(to_delete, reason)

    @cleanup.command(name='bot')
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def cleanup_bot(self, ctx: commands.Context, number: int):
        """Cleans up command messages and messages from the bot"""

        channel = ctx.message.channel
        author = ctx.message.author
        is_bot = self.bot.user.bot

        prefixes = self.bot.command_prefix
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        elif callable(prefixes):
            if asyncio.iscoroutine(prefixes):
                await ctx.send('Coroutine prefixes not yet implemented.')
                return
            prefixes = prefixes(self.bot, ctx.message)

        # In case some idiot sets a null prefix
        if '' in prefixes:
            prefixes.remove('')

        def check(m):
            if m.author.id == self.bot.user.id:
                return True
            elif m == ctx.message:
                return True
            p = discord.utils.find(m.content.startswith, prefixes)
            if p and len(p) > 0:
                return m.content[len(p):].startswith(tuple(self.bot.commands))
            return False

        to_delete = [ctx.message]

        tries_left = 5
        tmp = ctx.message

        while tries_left and len(to_delete) - 1 < number:
            async for message in channel.history(limit=100, before=tmp):
                if len(to_delete) - 1 < number and check(message) and\
                                (ctx.message.created_at - message.created_at).days < 14:
                    to_delete.append(message)
                elif (ctx.message.created_at - message.created_at).days >= 14:
                    tries_left = 0
                    break
                tmp = message
            if tries_left:
                tries_left -= 1

        reason = "{}({}) deleted {} "\
                 " command messages in channel {}"\
                 "".format(author.name, author.id, len(to_delete),
                           channel.name)
        logger.info(reason)

        if is_bot:
            await mass_purge(to_delete, channel, reason)
        else:
            await slow_deletion(to_delete, reason)

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
        is_bot = self.bot.user.bot

        # You can always delete your own messages, this is needed to purge
        can_mass_purge = False
        if type(author) is discord.Member:
            me = ctx.guild.me
            can_mass_purge = channel.permissions_for(me).manage_messages

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
            if m.author.id != self.bot.user.id:
                return False
            elif content_match(m.content):
                return True
            return False

        to_delete = []
        # Selfbot convenience, delete trigger message
        if author == self.bot.user:
            to_delete.append(ctx.message)
            number += 1

        tries_left = 5
        tmp = ctx.message
        while tries_left and len(to_delete) < number:
            async for message in channel.history(limit=100, before=tmp):
                if len(to_delete) < number and check(message) and\
                        (ctx.message.created_at - message.created_at).days < 14:
                    to_delete.append(message)
                elif (ctx.message.created_at - message.created_at).days >= 14:
                    # Found a message that is 14 or more days old, stop here
                    tries_left = 0
                    break
                tmp = message
            if tries_left:
                tries_left -= 1

        if channel.name:
            channel_name = 'channel ' + channel.name
        else:
            channel_name = str(channel)

        reason = "{}({}) deleted {} messages "\
                 "sent by the bot in {}"\
                 "".format(author.name, author.id, len(to_delete),
                           channel_name)
        logger.info(reason)

        if is_bot and can_mass_purge:
            await mass_purge(to_delete, channel, reason)
        else:
            await slow_deletion(to_delete, reason)
