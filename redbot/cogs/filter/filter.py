import discord
import re
from typing import Union, Set

from redbot.core import checks, Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import pagify

RE_WORD_SPLIT = re.compile(r"[^\w]")
_ = Translator("Filter", __file__)


@cog_i18n(_)
class Filter(commands.Cog):
    """Filter unwanted words and phrases from text channels."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.settings = Config.get_conf(self, 4766951341)
        default_guild_settings = {
            "filter": [],
            "filterban_count": 0,
            "filterban_time": 0,
            "filter_names": False,
            "filter_default_name": "John Doe",
        }
        default_member_settings = {"filter_count": 0, "next_reset_time": 0}
        default_channel_settings = {"filter": []}
        self.settings.register_guild(**default_guild_settings)
        self.settings.register_member(**default_member_settings)
        self.settings.register_channel(**default_channel_settings)
        self.register_task = self.bot.loop.create_task(self.register_filterban())

    def __unload(self):
        self.register_task.cancel()

    @staticmethod
    async def register_filterban():
        try:
            await modlog.register_casetype(
                "filterban", False, ":filing_cabinet: :hammer:", "Filter ban", "ban"
            )
        except RuntimeError:
            pass

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def filterset(self, ctx: commands.Context):
        """Manage filter settings."""
        pass

    @filterset.command(name="defaultname")
    async def filter_default_name(self, ctx: commands.Context, name: str):
        """Set the nickname for users with a filtered name.

        Note that this has no effect if filtering names is disabled
        (to toggle, run `[p]filter names`).

        The default name used is *John Doe*.
        """
        guild = ctx.guild
        await self.settings.guild(guild).filter_default_name.set(name)
        await ctx.send(_("The name to use on filtered names has been set."))

    @filterset.command(name="ban")
    async def filter_ban(self, ctx: commands.Context, count: int, timeframe: int):
        """Set the filter's autoban conditions.

        Users will be banned if they send `<count>` filtered words in
        `<timeframe>` seconds.

        Set both to zero to disable autoban.
        """
        if (count <= 0) != (timeframe <= 0):
            await ctx.send(
                _(
                    "Count and timeframe either both need to be 0 "
                    "or both need to be greater than 0!"
                )
            )
            return
        elif count == 0 and timeframe == 0:
            await self.settings.guild(ctx.guild).filterban_count.set(0)
            await self.settings.guild(ctx.guild).filterban_time.set(0)
            await ctx.send(_("Autoban disabled."))
        else:
            await self.settings.guild(ctx.guild).filterban_count.set(count)
            await self.settings.guild(ctx.guild).filterban_time.set(timeframe)
            await ctx.send(_("Count and time have been set."))

    @commands.group(name="filter")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _filter(self, ctx: commands.Context):
        """Add or remove words from server filter.

        Use double quotes to add or remove sentences.

        Using this command with no subcommands will send the list of
        the server's filtered words.
        """
        if ctx.invoked_subcommand is None:
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

    @_filter.group(name="channel")
    async def _filter_channel(self, ctx: commands.Context):
        """Add or remove words from channel filter.

        Use double quotes to add or remove sentences.

        Using this command with no subcommands will send the list of
        the channel's filtered words.
        """
        if ctx.invoked_subcommand is None:
            channel = ctx.channel
            author = ctx.author
            word_list = await self.settings.channel(channel).filter()
            if word_list:
                words = ", ".join(word_list)
                words = _("Filtered in this channel:") + "\n\n" + words
                try:
                    for page in pagify(words, delims=[" ", "\n"], shorten_by=8):
                        await author.send(page)
                except discord.Forbidden:
                    await ctx.send(_("I can't send direct messages to you."))

    @_filter_channel.command("add")
    async def filter_channel_add(self, ctx: commands.Context, *, words: str):
        """Add words to the filter.

        Use double quotes to add sentences.

        Examples:
        - `[p]filter channel add word1 word2 word3`
        - `[p]filter channel add "This is a sentence"`
        """
        channel = ctx.channel
        split_words = words.split()
        word_list = []
        tmp = ""
        for word in split_words:
            if not word.startswith('"') and not word.endswith('"') and not tmp:
                word_list.append(word)
            else:
                if word.startswith('"'):
                    tmp += word[1:] + " "
                elif word.endswith('"'):
                    tmp += word[:-1]
                    word_list.append(tmp)
                    tmp = ""
                else:
                    tmp += word + " "
        added = await self.add_to_filter(channel, word_list)
        if added:
            await ctx.send(_("Words added to filter."))
        else:
            await ctx.send(_("Words already in the filter."))

    @_filter_channel.command("remove")
    async def filter_channel_remove(self, ctx: commands.Context, *, words: str):
        """Remove words from the filter.

        Use double quotes to remove sentences.

        Examples:
        - `[p]filter channel remove word1 word2 word3`
        - `[p]filter channel remove "This is a sentence"`
        """
        channel = ctx.channel
        split_words = words.split()
        word_list = []
        tmp = ""
        for word in split_words:
            if not word.startswith('"') and not word.endswith('"') and not tmp:
                word_list.append(word)
            else:
                if word.startswith('"'):
                    tmp += word[1:] + " "
                elif word.endswith('"'):
                    tmp += word[:-1]
                    word_list.append(tmp)
                    tmp = ""
                else:
                    tmp += word + " "
        removed = await self.remove_from_filter(channel, word_list)
        if removed:
            await ctx.send(_("Words removed from filter."))
        else:
            await ctx.send(_("Those words weren't in the filter."))

    @_filter.command(name="add")
    async def filter_add(self, ctx: commands.Context, *, words: str):
        """Add words to the filter.

        Use double quotes to add sentences.

        Examples:
        - `[p]filter add word1 word2 word3`
        - `[p]filter add "This is a sentence"`
        """
        server = ctx.guild
        split_words = words.split()
        word_list = []
        tmp = ""
        for word in split_words:
            if not word.startswith('"') and not word.endswith('"') and not tmp:
                word_list.append(word)
            else:
                if word.startswith('"'):
                    tmp += word[1:] + " "
                elif word.endswith('"'):
                    tmp += word[:-1]
                    word_list.append(tmp)
                    tmp = ""
                else:
                    tmp += word + " "
        added = await self.add_to_filter(server, word_list)
        if added:
            await ctx.send(_("Words successfully added to filter."))
        else:
            await ctx.send(_("Those words were already in the filter."))

    @_filter.command(name="remove")
    async def filter_remove(self, ctx: commands.Context, *, words: str):
        """Remove words from the filter.

        Use double quotes to remove sentences.

        Examples:
        - `[p]filter remove word1 word2 word3`
        - `[p]filter remove "This is a sentence"`
        """
        server = ctx.guild
        split_words = words.split()
        word_list = []
        tmp = ""
        for word in split_words:
            if not word.startswith('"') and not word.endswith('"') and not tmp:
                word_list.append(word)
            else:
                if word.startswith('"'):
                    tmp += word[1:] + " "
                elif word.endswith('"'):
                    tmp += word[:-1]
                    word_list.append(tmp)
                    tmp = ""
                else:
                    tmp += word + " "
        removed = await self.remove_from_filter(server, word_list)
        if removed:
            await ctx.send(_("Words successfully removed from filter."))
        else:
            await ctx.send(_("Those words weren't in the filter."))

    @_filter.command(name="names")
    async def filter_names(self, ctx: commands.Context):
        """Toggle name and nickname filtering.

        This is disabled by default.
        """
        guild = ctx.guild
        current_setting = await self.settings.guild(guild).filter_names()
        await self.settings.guild(guild).filter_names.set(not current_setting)
        if current_setting:
            await ctx.send(_("Names and nicknames will no longer be filtered."))
        else:
            await ctx.send(_("Names and nicknames will now be filtered."))

    async def add_to_filter(
        self, server_or_channel: Union[discord.Guild, discord.TextChannel], words: list
    ) -> bool:
        added = False
        if isinstance(server_or_channel, discord.Guild):
            async with self.settings.guild(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower() not in cur_list and w:
                        cur_list.append(w.lower())
                        added = True

        elif isinstance(server_or_channel, discord.TextChannel):
            async with self.settings.channel(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower not in cur_list and w:
                        cur_list.append(w.lower())
                        added = True

        return added

    async def remove_from_filter(
        self, server_or_channel: Union[discord.Guild, discord.TextChannel], words: list
    ) -> bool:
        removed = False
        if isinstance(server_or_channel, discord.Guild):
            async with self.settings.guild(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower() in cur_list:
                        cur_list.remove(w.lower())
                        removed = True

        elif isinstance(server_or_channel, discord.TextChannel):
            async with self.settings.channel(server_or_channel).filter() as cur_list:
                for w in words:
                    if w.lower() in cur_list:
                        cur_list.remove(w.lower())
                        removed = True

        return removed

    async def filter_hits(
        self, text: str, server_or_channel: Union[discord.Guild, discord.TextChannel]
    ) -> Set[str]:
        if isinstance(server_or_channel, discord.Guild):
            word_list = set(await self.settings.guild(server_or_channel).filter())
        elif isinstance(server_or_channel, discord.TextChannel):
            word_list = set(
                await self.settings.guild(server_or_channel.guild).filter()
                + await self.settings.channel(server_or_channel).filter()
            )
        else:
            raise TypeError("%r should be Guild or TextChannel" % server_or_channel)

        content = text.lower()
        msg_words = set(RE_WORD_SPLIT.split(content))

        filtered_phrases = {x for x in word_list if len(RE_WORD_SPLIT.split(x)) > 1}
        filtered_words = word_list - filtered_phrases

        hits = {p for p in filtered_phrases if p in content}
        hits |= filtered_words & msg_words
        return hits

    async def check_filter(self, message: discord.Message):
        server = message.guild
        author = message.author

        filter_count = await self.settings.guild(server).filterban_count()
        filter_time = await self.settings.guild(server).filterban_time()
        user_count = await self.settings.member(author).filter_count()
        next_reset_time = await self.settings.member(author).next_reset_time()

        if filter_count > 0 and filter_time > 0:
            if message.created_at.timestamp() >= next_reset_time:
                next_reset_time = message.created_at.timestamp() + filter_time
                await self.settings.member(author).next_reset_time.set(next_reset_time)
                if user_count > 0:
                    user_count = 0
                    await self.settings.member(author).filter_count.set(user_count)

        hits = await self.filter_hits(message.content, message.channel)

        if hits:
            try:
                self.bot.dispatch("filter_message_delete", message)
                await message.delete()
            except discord.HTTPException:
                pass
            else:
                if filter_count > 0 and filter_time > 0:
                    user_count += 1
                    await self.settings.member(author).filter_count.set(user_count)
                    if (
                        user_count >= filter_count
                        and message.created_at.timestamp() < next_reset_time
                    ):
                        reason = _("Autoban (too many filtered messages.)")
                        try:
                            await server.ban(author, reason=reason)
                        except discord.HTTPException:
                            pass
                        else:
                            await modlog.create_case(
                                self.bot,
                                server,
                                message.created_at,
                                "filterban",
                                author,
                                server.me,
                                reason,
                            )

    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        if await self.bot.is_automod_immune(message):
            return

        await self.check_filter(message)

    async def on_message_edit(self, _prior, message):
        # message content has to change for non-bot's currently.
        # if this changes, we should compare before passing it.
        await self.on_message(message)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name != after.display_name:
            await self.maybe_filter_name(after)

    async def on_member_join(self, member: discord.Member):
        await self.maybe_filter_name(member)

    async def maybe_filter_name(self, member: discord.Member):
        if not member.guild.me.guild_permissions.manage_nicknames:
            return  # No permissions to manage nicknames, so can't do anything
        if member.top_role >= member.guild.me.top_role:
            return  # Discord Hierarchy applies to nicks
        if await self.bot.is_automod_immune(member):
            return
        if not await self.settings.guild(member.guild).filter_names():
            return

        word_list = await self.settings.guild(member.guild).filter()
        for w in word_list:
            if w in member.display_name.lower():
                name_to_use = await self.settings.guild(member.guild).filter_default_name()
                reason = _("Filtered nickname") if member.nick else _("Filtered name")
                try:
                    await member.edit(nick=name_to_use, reason=reason)
                except discord.HTTPException:
                    pass
                return
