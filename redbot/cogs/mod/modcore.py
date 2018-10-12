import asyncio
import contextlib
from datetime import datetime, timedelta
from collections import deque, defaultdict, namedtuple
from typing import cast

import discord

from redbot.core import checks, Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, escape
from .checks import mod_or_voice_permissions, admin_or_voice_permissions, bot_has_voice_permissions

from redbot.core.utils.common_filters import filter_invites, filter_various_mentions

from . import MuteMixin, KickBanMixin, MiscMixin, UtilsMixin

_ = T_ = Translator("Mod", __file__)


@cog_i18n(_)
class Mod(MuteMixin, KickBanMixin, MiscMixin, UtilsMixin, commands.Cog):
    """Moderation tools."""

    default_guild_settings = {
        "ban_mention_spam": False,
        "delete_repeats": False,
        "ignored": False,
        "respect_hierarchy": True,
        "delete_delay": -1,
        "reinvite_on_unban": False,
        "current_tempbans": [],
    }

    default_channel_settings = {"ignored": False}

    default_member_settings = {"past_nicks": [], "perms_cache": {}, "banned_until": False}

    default_user_settings = {"past_names": []}

    def __init__(self, bot: Red):
        self.bot = bot
        super().__init__()
        self.settings = Config.get_conf(self, 4961522000, force_registration=True)
        self.settings.register_guild(**self.default_guild_settings)
        self.settings.register_channel(**self.default_channel_settings)
        self.settings.register_member(**self.default_member_settings)
        self.settings.register_user(**self.default_user_settings)
        self.cache = defaultdict(lambda: deque(maxlen=3))
        self.last_case = defaultdict(dict)

    def __unload(self):
        super().__unload()

    async def _casetype_registration(self):
        casetypes_to_register = [
            {
                "name": "ban",
                "default_setting": True,
                "image": "\N{HAMMER}",
                "case_str": "Ban",
                "audit_type": "ban",
            },
            {
                "name": "kick",
                "default_setting": True,
                "image": "\N{WOMANS BOOTS}",
                "case_str": "Kick",
                "audit_type": "kick",
            },
            {
                "name": "hackban",
                "default_setting": True,
                "image": "\N{BUST IN SILHOUETTE}\N{HAMMER}",
                "case_str": "Hackban",
                "audit_type": "ban",
            },
            {
                "name": "tempban",
                "default_setting": True,
                "image": "\N{ALARM CLOCK}\N{HAMMER}",
                "case_str": "Tempban",
                "audit_type": "ban",
            },
            {
                "name": "softban",
                "default_setting": True,
                "image": "\N{DASH SYMBOL}\N{HAMMER}",
                "case_str": "Softban",
                "audit_type": "ban",
            },
            {
                "name": "unban",
                "default_setting": True,
                "image": "\N{DOVE OF PEACE}",
                "case_str": "Unban",
                "audit_type": "unban",
            },
            {
                "name": "voiceban",
                "default_setting": True,
                "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
                "case_str": "Voice Ban",
                "audit_type": "member_update",
            },
            {
                "name": "voiceunban",
                "default_setting": True,
                "image": "\N{SPEAKER}",
                "case_str": "Voice Unban",
                "audit_type": "member_update",
            },
            {
                "name": "vmute",
                "default_setting": False,
                "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
                "case_str": "Voice Mute",
                "audit_type": "overwrite_update",
            },
            {
                "name": "cmute",
                "default_setting": False,
                "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
                "case_str": "Channel Mute",
                "audit_type": "overwrite_update",
            },
            {
                "name": "smute",
                "default_setting": True,
                "image": "\N{SPEAKER WITH CANCELLATION STROKE}",
                "case_str": "Server Mute",
                "audit_type": "overwrite_update",
            },
            {
                "name": "vunmute",
                "default_setting": False,
                "image": "\N{SPEAKER}",
                "case_str": "Voice Unmute",
                "audit_type": "overwrite_update",
            },
            {
                "name": "cunmute",
                "default_setting": False,
                "image": "\N{SPEAKER}",
                "case_str": "Channel Unmute",
                "audit_type": "overwrite_update",
            },
            {
                "name": "sunmute",
                "default_setting": True,
                "image": "\N{SPEAKER}",
                "case_str": "Server Unmute",
                "audit_type": "overwrite_update",
            },
        ]
        try:
            await modlog.register_casetypes(casetypes_to_register)
        except RuntimeError:
            pass

    @commands.group()
    @commands.guild_only()
    @checks.guildowner_or_permissions(administrator=True)
    async def modset(self, ctx: commands.Context):
        """Manage server administration settings."""
        if ctx.invoked_subcommand is None:
            guild = ctx.guild
            # Display current settings
            delete_repeats = await self.settings.guild(guild).delete_repeats()
            ban_mention_spam = await self.settings.guild(guild).ban_mention_spam()
            respect_hierarchy = await self.settings.guild(guild).respect_hierarchy()
            delete_delay = await self.settings.guild(guild).delete_delay()
            reinvite_on_unban = await self.settings.guild(guild).reinvite_on_unban()
            msg = ""
            msg += _("Delete repeats: {yes_or_no}\n").format(
                yes_or_no=_("Yes") if delete_repeats else _("No")
            )
            msg += _("Ban mention spam: {num_mentions}\n").format(
                num_mentions=_("{num} mentions").format(num=ban_mention_spam)
                if ban_mention_spam
                else _("No")
            )
            msg += _("Respects hierarchy: {yes_or_no}\n").format(
                yes_or_no=_("Yes") if respect_hierarchy else _("No")
            )
            msg += _("Delete delay: {num_seconds}\n").format(
                num_seconds=_("{num} seconds").format(num=delete_delay)
                if delete_delay != -1
                else _("None")
            )
            msg += _("Reinvite on unban: {yes_or_no}\n").format(
                yes_or_no=_("Yes") if reinvite_on_unban else _("No")
            )
            await ctx.send(box(msg))

    @modset.command()
    @commands.guild_only()
    async def hierarchy(self, ctx: commands.Context):
        """Toggle role hierarchy check for mods and admins.

        **WARNING**: Disabling this setting will allow mods to take
        actions on users above them in the role hierarchy!

        This is enabled by default.
        """
        guild = ctx.guild
        toggled = await self.settings.guild(guild).respect_hierarchy()
        if not toggled:
            await self.settings.guild(guild).respect_hierarchy.set(True)
            await ctx.send(
                _("Role hierarchy will be checked when moderation commands are issued.")
            )
        else:
            await self.settings.guild(guild).respect_hierarchy.set(False)
            await ctx.send(
                _("Role hierarchy will be ignored when moderation commands are issued.")
            )

    @modset.command()
    @commands.guild_only()
    async def banmentionspam(self, ctx: commands.Context, max_mentions: int = 0):
        """Set the autoban conditions for mention spam.

        Users will be banned if they send any message which contains more than
        `<max_mentions>` mentions.

        `<max_mentions>` must be at least 5. Set to 0 to disable.
        """
        guild = ctx.guild
        if max_mentions:
            if max_mentions < 5:
                max_mentions = 5
            await self.settings.guild(guild).ban_mention_spam.set(max_mentions)
            await ctx.send(
                _(
                    "Autoban for mention spam enabled. "
                    "Anyone mentioning {max_mentions} or more different people "
                    "in a single message will be autobanned."
                ).format(max_mentions=max_mentions)
            )
        else:
            cur_setting = await self.settings.guild(guild).ban_mention_spam()
            if not cur_setting:
                await ctx.send_help()
                return
            await self.settings.guild(guild).ban_mention_spam.set(False)
            await ctx.send(_("Autoban for mention spam disabled."))

    @modset.command()
    @commands.guild_only()
    async def deleterepeats(self, ctx: commands.Context):
        """Enable auto-deletion of repeated messages."""
        guild = ctx.guild
        cur_setting = await self.settings.guild(guild).delete_repeats()
        if not cur_setting:
            await self.settings.guild(guild).delete_repeats.set(True)
            await ctx.send(_("Messages repeated up to 3 times will be deleted."))
        else:
            await self.settings.guild(guild).delete_repeats.set(False)
            await ctx.send(_("Repeated messages will be ignored."))

    @modset.command()
    @commands.guild_only()
    async def deletedelay(self, ctx: commands.Context, time: int = None):
        """Set the delay until the bot removes the command message.

        Must be between -1 and 60.

        Set to -1 to disable this feature.
        """
        guild = ctx.guild
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            await self.settings.guild(guild).delete_delay.set(time)
            if time == -1:
                await ctx.send(_("Command deleting disabled."))
            else:
                await ctx.send(_("Delete delay set to {num} seconds.").format(num=time))
        else:
            delay = await self.settings.guild(guild).delete_delay()
            if delay != -1:
                await ctx.send(
                    _(
                        "Bot will delete command messages after"
                        " {num} seconds. Set this value to -1 to"
                        " stop deleting messages"
                    ).format(num=delay)
                )
            else:
                await ctx.send(_("I will not delete command messages."))

    @modset.command()
    @commands.guild_only()
    async def reinvite(self, ctx: commands.Context):
        """Toggle whether an invite will be sent to a user when unbanned.

        If this is True, the bot will attempt to create and send a single-use invite
        to the newly-unbanned user.
        """
        guild = ctx.guild
        cur_setting = await self.settings.guild(guild).reinvite_on_unban()
        if not cur_setting:
            await self.settings.guild(guild).reinvite_on_unban.set(True)
            await ctx.send(
                _("Users unbanned with {command} will be reinvited.").format(f"{ctx.prefix}unban")
            )
        else:
            await self.settings.guild(guild).reinvite_on_unban.set(False)
            await ctx.send(
                _("Users unbanned with {command} will not be reinvited.").format(
                    f"{ctx.prefix}unban"
                )
            )

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context):
        """Add servers or channels to the ignore list."""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.count_ignored())

    @ignore.command(name="channel")
    async def ignore_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Ignore commands in the channel.

        Defaults to the current channel.
        """
        if not channel:
            channel = ctx.channel
        if not await self.settings.channel(channel).ignored():
            await self.settings.channel(channel).ignored.set(True)
            await ctx.send(_("Channel added to ignore list."))
        else:
            await ctx.send(_("Channel already in ignore list."))

    @ignore.command(name="server", aliases=["guild"])
    @checks.admin_or_permissions(manage_guild=True)
    async def ignore_guild(self, ctx: commands.Context):
        """Ignore commands in this server."""
        guild = ctx.guild
        if not await self.settings.guild(guild).ignored():
            await self.settings.guild(guild).ignored.set(True)
            await ctx.send(_("This server has been added to the ignore list."))
        else:
            await ctx.send(_("This server is already being ignored."))

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def unignore(self, ctx: commands.Context):
        """Remove servers or channels from the ignore list."""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.count_ignored())

    @unignore.command(name="channel")
    async def unignore_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Remove a channel from ignore the list.

        Defaults to the current channel.
        """
        if not channel:
            channel = ctx.channel

        if await self.settings.channel(channel).ignored():
            await self.settings.channel(channel).ignored.set(False)
            await ctx.send(_("Channel removed from ignore list."))
        else:
            await ctx.send(_("That channel is not in the ignore list."))

    @unignore.command(name="server", aliases=["guild"])
    @checks.admin_or_permissions(manage_guild=True)
    async def unignore_guild(self, ctx: commands.Context):
        """Remove this server from the ignore list."""
        guild = ctx.message.guild
        if await self.settings.guild(guild).ignored():
            await self.settings.guild(guild).ignored.set(False)
            await ctx.send(_("This server has been removed from the ignore list."))
        else:
            await ctx.send(_("This server is not in the ignore list."))

    async def count_ignored(self):
        ch_count = 0
        svr_count = 0
        for guild in self.bot.guilds:
            if not await self.settings.guild(guild).ignored():
                for channel in guild.text_channels:
                    if await self.settings.channel(channel).ignored():
                        ch_count += 1
            else:
                svr_count += 1
        msg = _("Currently ignoring:\n{} channels\n{} guilds\n").format(ch_count, svr_count)
        return box(msg)

    async def __global_check(self, ctx):
        """Global check to see if a channel or server is ignored.

        Any users who have permission to use the `ignore` or `unignore` commands
        surpass the check.
        """
        perms = ctx.channel.permissions_for(ctx.author)
        surpass_ignore = (
            isinstance(ctx.channel, discord.abc.PrivateChannel)
            or perms.manage_guild
            or await ctx.bot.is_owner(ctx.author)
            or await ctx.bot.is_admin(ctx.author)
        )
        if surpass_ignore:
            return True
        guild_ignored = await self.settings.guild(ctx.guild).ignored()
        chann_ignored = await self.settings.channel(ctx.channel).ignored()
        return not (guild_ignored or chann_ignored and not perms.manage_channels)

    async def check_duplicates(self, message):
        guild = message.guild
        author = message.author

        if await self.settings.guild(guild).delete_repeats():
            if not message.content:
                return False
            self.cache[author].append(message)
            msgs = self.cache[author]
            if len(msgs) == 3 and msgs[0].content == msgs[1].content == msgs[2].content:
                try:
                    await message.delete()
                    return True
                except discord.HTTPException:
                    pass
        return False

    async def check_mention_spam(self, message):
        guild = message.guild
        author = message.author

        max_mentions = await self.settings.guild(guild).ban_mention_spam()
        if max_mentions:
            mentions = set(message.mentions)
            if len(mentions) >= max_mentions:
                try:
                    await guild.ban(author, reason=_("Mention spam (Autoban)"))
                except discord.HTTPException:
                    self.log.info(
                        "Failed to ban member for mention spam in server {}.".format(guild.id)
                    )
                else:
                    try:
                        await modlog.create_case(
                            self.bot,
                            guild,
                            message.created_at,
                            "ban",
                            author,
                            guild.me,
                            _("Mention spam (Autoban)"),
                            until=None,
                            channel=None,
                        )
                    except RuntimeError as e:
                        print(e)
                        return False
                    return True
        return False

    async def on_command_completion(self, ctx: commands.Context):
        await self._delete_delay(ctx)

    # noinspection PyUnusedLocal
    async def on_command_error(self, ctx: commands.Context, error):
        await self._delete_delay(ctx)

    async def _delete_delay(self, ctx: commands.Context):
        """Currently used for:
            * delete delay"""
        guild = ctx.guild
        if guild is None:
            return
        message = ctx.message
        delay = await self.settings.guild(guild).delete_delay()

        if delay == -1:
            return

        async def _delete_helper(m):
            with contextlib.suppress(discord.HTTPException):
                await m.delete()
                self.log.debug("Deleted command msg {}".format(m.id))

        await asyncio.sleep(delay)
        await _delete_helper(message)

    async def on_message(self, message):
        author = message.author
        if message.guild is None or self.bot.user == author:
            return
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        #  Bots and mods or superior are ignored from the filter
        mod_or_superior = await self.is_mod_or_superior(self.bot, obj=author)
        if mod_or_superior:
            return
        # As are anyone configured to be
        if await self.bot.is_automod_immune(message):
            return
        deleted = await self.check_duplicates(message)
        if not deleted:
            await self.check_mention_spam(message)

    async def on_member_ban(self, guild: discord.Guild, member: discord.Member):
        if (guild.id, member.id) in self.ban_queue:
            self.ban_queue.remove((guild.id, member.id))
            return
        try:
            await modlog.get_modlog_channel(guild)
        except RuntimeError:
            return  # No modlog channel so no point in continuing
        mod, reason, date = await self.get_audit_entry_info(
            guild, discord.AuditLogAction.ban, member
        )
        if date is None:
            date = datetime.now()
        try:
            await modlog.create_case(
                self.bot, guild, date, "ban", member, mod, reason if reason else None
            )
        except RuntimeError as e:
            print(e)

    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        if (guild.id, user.id) in self.unban_queue:
            self.unban_queue.remove((guild.id, user.id))
            return
        try:
            await modlog.get_modlog_channel(guild)
        except RuntimeError:
            return  # No modlog channel so no point in continuing
        mod, reason, date = await self.get_audit_entry_info(
            guild, discord.AuditLogAction.unban, user
        )
        if date is None:
            date = datetime.now()
        try:
            await modlog.create_case(self.bot, guild, date, "unban", user, mod, reason)
        except RuntimeError as e:
            print(e)

    @staticmethod
    async def on_modlog_case_create(case: modlog.Case):
        """
        An event for modlog case creation
        """
        mod_channel = await modlog.get_modlog_channel(case.guild)
        if mod_channel is None:
            return
        use_embeds = await case.bot.embed_requested(mod_channel, case.guild.me)
        case_content = await case.message_content(use_embeds)
        if use_embeds:
            msg = await mod_channel.send(embed=case_content)
        else:
            msg = await mod_channel.send(case_content)
        await case.edit({"message": msg})

    @staticmethod
    async def on_modlog_case_edit(case: modlog.Case):
        """
        Event for modlog case edits
        """
        if not case.message:
            return
        use_embed = await case.bot.embed_requested(case.message.channel, case.guild.me)
        case_content = await case.message_content(use_embed)
        if use_embed:
            await case.message.edit(embed=case_content)
        else:
            await case.message.edit(content=case_content)

    @classmethod
    async def get_audit_entry_info(
        cls, guild: discord.Guild, action: discord.AuditLogAction, target
    ):
        """Get info about an audit log entry.

        Parameters
        ----------
        guild : discord.Guild
            Same as ``guild`` in `get_audit_log_entry`.
        action : int
            Same as ``action`` in `get_audit_log_entry`.
        target : `discord.User` or `discord.Member`
            Same as ``target`` in `get_audit_log_entry`.

        Returns
        -------
        tuple
            A tuple in the form``(mod: discord.Member, reason: str,
            date_created: datetime.datetime)``. Returns ``(None, None, None)``
            if the audit log entry could not be found.
        """
        try:
            entry = await cls.get_audit_log_entry(guild, action=action, target=target)
        except discord.HTTPException:
            entry = None
        if entry is None:
            return None, None, None
        return entry.user, entry.reason, entry.created_at

    @staticmethod
    async def get_audit_log_entry(guild: discord.Guild, action: discord.AuditLogAction, target):
        """Get an audit log entry.

        Any exceptions encountered when looking through the audit log will be
        propogated out of this function.

        Parameters
        ----------
        guild : discord.Guild
            The guild for the audit log.
        action : int
            The audit log action (see `discord.AuditLogAction`).
        target : `discord.Member` or `discord.User`
            The target of the audit log action.

        Returns
        -------
        discord.AuditLogEntry
            The audit log entry. Returns ``None`` if not found.

        """
        async for entry in guild.audit_logs(action=action):
            if entry.target == target:
                return entry

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.name != after.name:
            async with self.settings.user(before).past_names() as name_list:
                while None in name_list:  # clean out null entries from a bug
                    name_list.remove(None)
                if after.name in name_list:
                    # Ensure order is maintained without duplicates occuring
                    name_list.remove(after.name)
                name_list.append(after.name)
                while len(name_list) > 20:
                    name_list.pop(0)

        if before.nick != after.nick and after.nick is not None:
            async with self.settings.member(before).past_nicks() as nick_list:
                while None in nick_list:  # clean out null entries from a bug
                    nick_list.remove(None)
                if after.nick in nick_list:
                    nick_list.remove(after.nick)
                nick_list.append(after.nick)
                while len(nick_list) > 20:
                    nick_list.pop(0)



