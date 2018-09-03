import discord
from typing import Union

from redbot.core import checks, Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.mod import is_mod_or_superior

_ = Translator("Filter", __file__)


@cog_i18n(_)
class Filter:
    """Filter-related commands"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.settings = Config.get_conf(self, 4766951341)
        default_guild_settings = {
            "filter": [],
            "filterban_count": 0,
            "filterban_time": 0,
            "filter_names": False,
            "filter_default_name": "John Doe",
            "exempt_users": [],
            "exempt_roles": [],
        }
        default_member_settings = {"filter_count": 0, "next_reset_time": 0}
        default_channel_settings = {"filter": []}
        self.settings.register_guild(**default_guild_settings)
        self.settings.register_member(**default_member_settings)
        self.settings.register_channel(**default_channel_settings)
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

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    async def filterset(self, ctx: commands.Context):
        """
        Filter settings
        """
        pass

    @filterset.command(name="defaultname")
    async def filter_default_name(self, ctx: commands.Context, name: str):
        """Sets the default name to use if filtering names is enabled

        Note that this has no effect if filtering names is disabled

        The default name used is John Doe
        """
        guild = ctx.guild
        await self.settings.guild(guild).filter_default_name.set(name)
        await ctx.send(_("The name to use on filtered names has been set."))

    @filterset.command(name="ban")
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

    @filterset.command(name="exempt")
    async def filter_exempt(
        self, ctx: commands.Context, user_or_role: Union[discord.Member, discord.Role]
    ):
        """
        Exempt the specified user or role from filters in this server
        """
        mod_role = ctx.bot.db.guild(ctx.guild).mod_role()
        admin_role = ctx.bot.db.guild(ctx.guild).admin_role()

        if isinstance(user_or_role, discord.Member) and user_or_role == ctx.guild.owner:
            await ctx.send(
                _(
                    "The specified member is already exempt from the filter by default because they are the server owner!"
                )
            )
            return
        elif isinstance(user_or_role, discord.Role) and user_or_role.id in (mod_role, admin_role):
            await ctx.send(
                _(
                    "The specified role is already exempt from the filter by default because it is the mod or admin role for this server!"
                )
            )
            return
        if isinstance(user_or_role, discord.Member):
            async with self.settings.guild(ctx.guild).exempt_users() as exempt_users:
                if user_or_role.id in exempt_users:
                    exempt_users.remove(user_or_role.id)
                    await ctx.send(
                        _("Member {0.name} is no longer exempt from the filter").format(
                            user_or_role
                        )
                    )
                else:
                    exempt_users.append(user_or_role.id)
                    await ctx.send(
                        _("Member {0.name} is now exempt from the filter").format(user_or_role)
                    )
        elif isinstance(user_or_role, discord.Role):
            async with self.settings.guild(ctx.guild).exempt_roles() as exempt_roles:
                if user_or_role.id in exempt_roles:
                    exempt_roles.remove(user_or_role.id)
                    await ctx.send(
                        _("Role {0.name} is no longer exempt from the filter").format(user_or_role)
                    )
                else:
                    exempt_roles.append(user_or_role.id)
                    await ctx.send(
                        _("Role {0.name} is now exempt from the filter").format(user_or_role)
                    )

    @commands.group(name="filter")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    async def _filter(self, ctx: commands.Context):
        """Adds/removes words from server filter

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

    @_filter.group(name="channel")
    async def _filter_channel(self, ctx: commands.Context):
        """Adds/removes words from channel filter

        Use double quotes to add/remove sentences
        Using this command with no subcommands will send
        the list of the channel's filtered words."""
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
        """Adds words to the filter

        Use double quotes to add sentences
        Examples:
        filter add word1 word2 word3
        filter add \"This is a sentence\""""
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
        """Remove words from the filter

        Use double quotes to remove sentences
        Examples:
        filter remove word1 word2 word3
        filter remove \"This is a sentence\""""
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
                    tmp += word[1:]
                elif word.endswith('"'):
                    tmp += word[:-1]
                    word_list.append(tmp)
                    tmp = ""
                else:
                    tmp += word
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
                    tmp += word[1:]
                elif word.endswith('"'):
                    tmp += word[:-1]
                    word_list.append(tmp)
                    tmp = ""
                else:
                    tmp += word
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

    async def check_filter(self, message: discord.Message):
        server = message.guild
        author = message.author
        word_list = set(
            await self.settings.guild(server).filter()
            + self.settings.channel(message.channel).filter()
        )
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

    async def is_exempt(self, user: discord.Member):
        if await is_mod_or_superior(self.bot, obj=user):
            return True

        if user == user.guild.owner:
            return True

        user_exemptions_list = await self.settings.guild(user.guild).exempt_users()
        if user.id in user_exemptions_list:
            return True

        role_exemptions_list = await self.settings.guild(user.guild).exempt_roles()
        for r in user.roles:
            if r.id in role_exemptions_list:
                return True
        return False

    async def on_message(self, message: discord.Message):
        if isinstance(message.channel, discord.abc.PrivateChannel):
            return
        author = message.author
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        #  Bots and mods or superior are ignored from the filter
        if await self.is_exempt(author):
            return

        await self.check_filter(message)

    async def on_message_edit(self, _, message):
        author = message.author
        if message.guild is None or self.bot.user == author:
            return
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        #  Bots and mods or superior are ignored from the filter
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if mod_or_superior:
            return

        await self.check_filter(message)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not after.guild.me.guild_permissions.manage_nicknames:
            return  # No permissions to manage nicknames, so can't do anything
        word_list = await self.settings.guild(after.guild).filter()
        filter_names = await self.settings.guild(after.guild).filter_names()
        name_to_use = await self.settings.guild(after.guild).filter_default_name()
        if not filter_names:
            return

        name_filtered = False
        nick_filtered = False

        for w in word_list:
            if w in after.name:
                name_filtered = True
            if after.nick and w in after.nick:  # since Member.nick can be None
                nick_filtered = True
            if name_filtered and nick_filtered:  # Both true, so break from loop
                break

        if name_filtered and after.nick is None:
            try:
                await after.edit(nick=name_to_use, reason="Filtered name")
            except:
                pass
        elif nick_filtered:
            try:
                await after.edit(nick=None, reason="Filtered nickname")
            except:
                pass

    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if not guild.me.guild_permissions.manage_nicknames:
            return
        word_list = await self.settings.guild(guild).filter()
        filter_names = await self.settings.guild(guild).filter_names()
        name_to_use = await self.settings.guild(guild).filter_default_name()

        if not filter_names:
            return

        for w in word_list:
            if w in member.name:
                try:
                    await member.edit(nick=name_to_use, reason="Filtered name")
                except:
                    pass
                break
