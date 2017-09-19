import logging
from typing import Tuple

import discord
from discord.ext import commands

from redbot.core import checks, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import pagify
from .common import is_allowed_by_hierarchy, is_mod_or_superior
from redbot.core.i18n import CogI18n

_ = CogI18n("Filter", __file__)


class Filter:
    """Filter-related commands"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, 4766951341)
        default_guild_settings = {
            "filter": []
        }
        self.settings.register_guild(**default_guild_settings)

    @commands.group(name="filter")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _filter(self, ctx: commands.Context):
        """Adds/removes words from filter

        Use double quotes to add/remove sentences
        Using this command with no subcommands will send
        the list of the server's filtered words."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            server = ctx.guild
            author = ctx.author
            word_list = await self.settings.guild(server).filter()
            if word_list:
                words = ", ".join(word_list)
                words = _("Filtered in this server:") + "\n\n" + words
                try:
                    for page in pagify(words, delims=[" ", "\n"], shorten_by=8):
                        await author.send(page)
                except discord.Forbidden:
                    await ctx.send(_("I can't send direct messages to you."))

    @_filter.command(name="add")
    async def filter_add(self, ctx: commands.Context, *words: str):
        """Adds words to the filter

        Use double quotes to add sentences
        Examples:
        filter add word1 word2 word3
        filter add \"This is a sentence\""""
        if words == ():
            await self.bot.send_cmd_help(ctx)
            return
        server = ctx.guild
        added = await self.add_to_filter(server, words)
        if added:
            await ctx.send(_("Words added to filter."))
        else:
            await ctx.send(_("Words already in the filter."))

    @_filter.command(name="remove")
    async def filter_remove(self, ctx: commands.Context, *words: str):
        """Remove words from the filter

        Use double quotes to remove sentences
        Examples:
        filter remove word1 word2 word3
        filter remove \"This is a sentence\""""
        if words == ():
            await self.bot.send_cmd_help(ctx)
            return
        server = ctx.guild
        removed = await self.remove_from_filter(server, words)
        if removed:
            await ctx.send(_("Words removed from filter."))
        else:
            await ctx.send(_("Those words weren't in the filter."))

    async def add_to_filter(self, server: discord.Guild, *words: tuple) -> bool:
        added = 0
        cur_list = await self.settings.guild(server).filter()
        for w in words:
            if w.lower() not in cur_list and w != "":
                cur_list.append(w.lower())
                added += 1
        if added:
            await self.settings.guild(server).filter.set(cur_list)
            return True
        else:
            return False

    async def remove_from_filter(self, server: discord.Guild, *words: tuple) -> bool:
        removed = 0
        cur_list = await self.settings.guild(server).filter()
        for w in words:
            if w.lower() in cur_list:
                cur_list.remove(w.lower())
                removed += 1
        if removed:
            await self.settings.guild(server).filter.set(cur_list)
            return True
        else:
            return False

    async def check_filter(self, message: discord.Message):
        server = message.guild
        word_list = await self.settings.guild(server).filter()
        if word_list:
            for w in word_list:
                if w in message.content.lower():
                    try:
                        await message.delete()
                    except:
                        pass

    async def on_message(self, message: discord.Message):
        if message.channel.guild is None:
            return
        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot

        #  Bots and mods or superior are ignored from the filter
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if not valid_user or mod_or_superior:
            return

        await self.check_filter(message)

    async def on_message_edit(self, _, message):
        author = message.author
        if message.guild is None or self.bot.user == author:
            return

        valid_user = isinstance(author, discord.Member) and not author.bot
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if not valid_user or mod_or_superior:
            return

        await self.check_filter(message)
