import discord

from redbot.core import checks, Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.mod import is_mod_or_superior

_ = Translator("Filter", __file__)


@cog_i18n(_)
class Filter(commands.Cog):
    """Filter-related commands"""

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
        self.settings.register_guild(**default_guild_settings)
        self.settings.register_member(**default_member_settings)
        self.register_task = self.bot.loop.create_task(self.register_filterban())

    def __unload(self):
        self.register_task.cancel()

    async def register_filterban(self):
        try:
            await modlog.register_casetype(
                "filterban", False, ":filing_cabinet: :hammer:", "Filter ban", "ban"
            )
        except RuntimeError:
            pass

    @commands.group(name="filter")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _filter(self, ctx: commands.Context):
        """Adds/removes words from filter

        Use double quotes to add/remove sentences
        Using this command with no subcommands will send
        the list of the server's filtered words."""
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

    @_filter.command(name="add")
    async def filter_add(self, ctx: commands.Context, *, words: str):
        """Adds words to the filter

        Use double quotes to add sentences
        Examples:
        filter add word1 word2 word3
        filter add \"This is a sentence\""""
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
            await ctx.send(_("Words added to filter."))
        else:
            await ctx.send(_("Words already in the filter."))

    @_filter.command(name="remove")
    async def filter_remove(self, ctx: commands.Context, *, words: str):
        """Remove words from the filter

        Use double quotes to remove sentences
        Examples:
        filter remove word1 word2 word3
        filter remove \"This is a sentence\""""
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
            await ctx.send(_("Words removed from filter."))
        else:
            await ctx.send(_("Those words weren't in the filter."))

    @_filter.command(name="names")
    async def filter_names(self, ctx: commands.Context):
        """Toggles whether or not to check names and nicknames against the filter

        This is disabled by default
        """
        guild = ctx.guild
        current_setting = await self.settings.guild(guild).filter_names()
        await self.settings.guild(guild).filter_names.set(not current_setting)
        if current_setting:
            await ctx.send(_("Names and nicknames will no longer be checked against the filter."))
        else:
            await ctx.send(_("Names and nicknames will now be checked against the filter."))

    @_filter.command(name="defaultname")
    async def filter_default_name(self, ctx: commands.Context, name: str):
        """Sets the default name to use if filtering names is enabled

        Note that this has no effect if filtering names is disabled

        The default name used is John Doe
        """
        guild = ctx.guild
        await self.settings.guild(guild).filter_default_name.set(name)
        await ctx.send(_("The name to use on filtered names has been set."))

    @_filter.command(name="ban")
    async def filter_ban(self, ctx: commands.Context, count: int, timeframe: int):
        """Autobans if the specified number of messages are filtered in the timeframe

        The timeframe is represented by seconds.
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

    async def add_to_filter(self, server: discord.Guild, words: list) -> bool:
        added = False
        async with self.settings.guild(server).filter() as cur_list:
            for w in words:
                if w.lower() not in cur_list and w:
                    cur_list.append(w.lower())
                    added = True

        return added

    async def remove_from_filter(self, server: discord.Guild, words: list) -> bool:
        removed = False
        async with self.settings.guild(server).filter() as cur_list:
            for w in words:
                if w.lower() in cur_list:
                    cur_list.remove(w.lower())
                    removed = True

        return removed

    async def check_filter(self, message: discord.Message):
        server = message.guild
        author = message.author
        word_list = await self.settings.guild(server).filter()
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

        if word_list:
            for w in word_list:
                if w in message.content.lower():
                    try:
                        await message.delete()
                    except:
                        pass
                    else:
                        if filter_count > 0 and filter_time > 0:
                            user_count += 1
                            await self.settings.member(author).filter_count.set(user_count)
                            if (
                                user_count >= filter_count
                                and message.created_at.timestamp() < next_reset_time
                            ):
                                reason = "Autoban (too many filtered messages.)"
                                try:
                                    await server.ban(author, reason=reason)
                                except:
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

        #  Bots and mods or superior are ignored from the filter
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if mod_or_superior:
            return
        # As is anyone configured to be
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
        word_list = await self.settings.guild(member.guild).filter()
        if not await self.settings.guild(member.guild).filter_names():
            return

        for w in word_list:
            if w in member.display_name.lower():
                name_to_use = await self.settings.guild(member.guild).filter_default_name()
                reason = "Filtered nick" if member.nick else "Filtered name"
                try:
                    await member.edit(nick=name_to_use, reason=reason)
                except discord.HTTPException:
                    pass
                return
