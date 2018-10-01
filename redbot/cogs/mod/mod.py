import asyncio
from datetime import datetime, timedelta
from collections import deque, defaultdict, namedtuple
from typing import Union, Optional

import discord

from redbot.core import checks, Config, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, escape, pagify
from .checks import mod_or_voice_permissions, admin_or_voice_permissions, bot_has_voice_permissions
from redbot.core.utils.mod import is_mod_or_superior, is_allowed_by_hierarchy, get_audit_reason
from .log import log
from .mod_converters import mute_converter

from redbot.core.utils.common_filters import filter_invites, filter_various_mentions

_ = Translator("Mod", __file__)


@cog_i18n(_)
class Mod(commands.Cog):
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
        super().__init__()
        self.bot = bot
        self.settings = Config.get_conf(self, 4961522000, force_registration=True)

        self.settings.register_guild(**self.default_guild_settings)
        self.settings.register_channel(**self.default_channel_settings)
        self.settings.register_member(**self.default_member_settings)
        self.settings.register_user(**self.default_user_settings)
        self.settings.register_custom("TEMPMUTE", user=None, channels=[], expiry=None, guild=None)
        self.ban_queue = []
        self.unban_queue = []
        self.cache = defaultdict(lambda: deque(maxlen=3))

        self.registration_task = self.bot.loop.create_task(self._casetype_registration())
        self.tban_expiry_task = self.bot.loop.create_task(self.check_tempban_expirations())
        self.last_case = defaultdict(dict)
        self.tmute_expiry_task = self.bot.loop.create_task(self.check_tempmute_expirations())
        self.scheduled_unmute_tasks = {}

    def __unload(self):
        self.registration_task.cancel()
        self.tban_expiry_task.cancel()
        self.tmute_expiry_task.cancel()
        for task in self.scheduled_unmute_tasks.values():
            if not task.done():
                task.cancel()

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
        """Manages server administration settings."""
        if ctx.invoked_subcommand is None:
            guild = ctx.guild
            # Display current settings
            delete_repeats = await self.settings.guild(guild).delete_repeats()
            ban_mention_spam = await self.settings.guild(guild).ban_mention_spam()
            respect_hierarchy = await self.settings.guild(guild).respect_hierarchy()
            delete_delay = await self.settings.guild(guild).delete_delay()
            reinvite_on_unban = await self.settings.guild(guild).reinvite_on_unban()
            msg = ""
            msg += "Delete repeats: {}\n".format("Yes" if delete_repeats else "No")
            msg += "Ban mention spam: {}\n".format(
                "{} mentions".format(ban_mention_spam)
                if isinstance(ban_mention_spam, int)
                else "No"
            )
            msg += "Respects hierarchy: {}\n".format("Yes" if respect_hierarchy else "No")
            msg += "Delete delay: {}\n".format(
                "{} seconds".format(delete_delay) if delete_delay != -1 else "None"
            )
            msg += "Reinvite on unban: {}".format("Yes" if reinvite_on_unban else "No")
            await ctx.send(box(msg))

    @modset.command()
    @commands.guild_only()
    async def hierarchy(self, ctx: commands.Context):
        """Toggles role hierarchy check for mods / admins"""
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
    async def banmentionspam(self, ctx: commands.Context, max_mentions: int = False):
        """Enables auto ban for messages mentioning X different people

        Accepted values: 5 or superior"""
        guild = ctx.guild
        if max_mentions:
            if max_mentions < 5:
                max_mentions = 5
            await self.settings.guild(guild).ban_mention_spam.set(max_mentions)
            await ctx.send(
                _(
                    "Autoban for mention spam enabled. "
                    "Anyone mentioning {} or more different people "
                    "in a single message will be autobanned."
                ).format(max_mentions)
            )
        else:
            cur_setting = await self.settings.guild(guild).ban_mention_spam()
            if cur_setting is False:
                await ctx.send_help()
                return
            await self.settings.guild(guild).ban_mention_spam.set(False)
            await ctx.send(_("Autoban for mention spam disabled."))

    @modset.command()
    @commands.guild_only()
    async def deleterepeats(self, ctx: commands.Context):
        """Enables auto deletion of repeated messages"""
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
        """Sets the delay until the bot removes the command message.

        Must be between -1 and 60.

        A delay of -1 means the bot will not remove the message."""
        guild = ctx.guild
        if time is not None:
            time = min(max(time, -1), 60)  # Enforces the time limits
            await self.settings.guild(guild).delete_delay.set(time)
            if time == -1:
                await ctx.send(_("Command deleting disabled."))
            else:
                await ctx.send(_("Delete delay set to {} seconds.").format(time))
        else:
            delay = await self.settings.guild(guild).delete_delay()
            if delay != -1:
                await ctx.send(
                    _(
                        "Bot will delete command messages after"
                        " {} seconds. Set this value to -1 to"
                        " stop deleting messages"
                    ).format(delay)
                )
            else:
                await ctx.send(_("I will not delete command messages."))

    @modset.command()
    @commands.guild_only()
    async def reinvite(self, ctx: commands.Context):
        """Toggles whether an invite will be sent when a user is unbanned via [p]unban.

        If this is True, the bot will attempt to create and send a single-use invite
        to the newly-unbanned user"""
        guild = ctx.guild
        cur_setting = await self.settings.guild(guild).reinvite_on_unban()
        if not cur_setting:
            await self.settings.guild(guild).reinvite_on_unban.set(True)
            await ctx.send(_("Users unbanned with {} will be reinvited.").format("[p]unban"))
        else:
            await self.settings.guild(guild).reinvite_on_unban.set(False)
            await ctx.send(_("Users unbanned with {} will not be reinvited.").format("[p]unban"))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kicks user.

        If a reason is specified, it will be the reason that shows up
        in the audit log"""
        author = ctx.author
        guild = ctx.guild

        if author == user:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}")
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif ctx.guild.me.top_role <= user.top_role or user == ctx.guild.owner:
            await ctx.send(_("I cannot do that due to discord hierarchy rules"))
            return
        audit_reason = get_audit_reason(author, reason)
        try:
            await guild.kick(user, reason=audit_reason)
            log.info("{}({}) kicked {}({})".format(author.name, author.id, user.name, user.id))
        except discord.errors.Forbidden:
            await ctx.send(_("I'm not allowed to do that."))
        except Exception as e:
            print(e)
        else:
            await ctx.send(_("Done. That felt good."))

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "kick",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def ban(
        self, ctx: commands.Context, user: discord.Member, days: str = None, *, reason: str = None
    ):
        """Bans user and deletes last X days worth of messages.

        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. Defaults to 0."""
        author = ctx.author
        guild = ctx.guild

        if author == user:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}")
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif ctx.guild.me.top_role <= user.top_role or user == ctx.guild.owner:
            await ctx.send(_("I cannot do that due to discord hierarchy rules"))
            return

        if days:
            if days.isdigit():
                days = int(days)
            else:
                if reason:
                    reason = "{} {}".format(days, reason)
                else:
                    reason = days
                days = 0
        else:
            days = 0

        audit_reason = get_audit_reason(author, reason)

        if days < 0 or days > 7:
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return
        queue_entry = (guild.id, user.id)
        self.ban_queue.append(queue_entry)
        try:
            await guild.ban(user, reason=audit_reason, delete_message_days=days)
            log.info(
                "{}({}) banned {}({}), deleting {} days worth of messages".format(
                    author.name, author.id, user.name, user.id, str(days)
                )
            )
        except discord.Forbidden:
            self.ban_queue.remove(queue_entry)
            await ctx.send(_("I'm not allowed to do that."))
        except Exception as e:
            self.ban_queue.remove(queue_entry)
            print(e)
        else:
            await ctx.send(_("Done. It was about time."))

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "ban",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def hackban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Preemptively bans user from the server

        A user ID needs to be provided in order to ban
        using this command"""
        author = ctx.author
        guild = ctx.guild
        if not guild.me.guild_permissions.ban_members:
            return await ctx.send(_("I lack the permissions to do this."))
        is_banned = False
        ban_list = await guild.bans()
        for entry in ban_list:
            if entry.user.id == user_id:
                is_banned = True
                break

        if is_banned:
            await ctx.send(_("User is already banned."))
            return

        user = guild.get_member(user_id)
        if user is not None:
            # Instead of replicating all that handling... gets attr from decorator
            return await ctx.invoke(self.ban, user, None, reason=reason)
        user = discord.Object(id=user_id)  # User not in the guild, but

        audit_reason = get_audit_reason(author, reason)
        queue_entry = (guild.id, user_id)
        self.ban_queue.append(queue_entry)
        try:
            await guild.ban(user, reason=audit_reason)
            log.info("{}({}) hackbanned {}".format(author.name, author.id, user_id))
        except discord.NotFound:
            self.ban_queue.remove(queue_entry)
            await ctx.send(_("User not found. Have you provided the correct user ID?"))
        except discord.Forbidden:
            self.ban_queue.remove(queue_entry)
            await ctx.send(_("I lack the permissions to do this."))
        else:
            await ctx.send(_("Done. The user will not be able to join this server."))

        user_info = await self.bot.get_user_info(user_id)
        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "hackban",
                user_info,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def tempban(
        self, ctx: commands.Context, user: discord.Member, days: int = 1, *, reason: str = None
    ):
        """Tempbans the user for the specified number of days"""
        guild = ctx.guild
        author = ctx.author
        days_delta = timedelta(days=int(days))
        unban_time = datetime.utcnow() + days_delta
        channel = ctx.channel
        can_ban = channel.permissions_for(guild.me).ban_members

        invite = await self.get_invite_for_reinvite(ctx, int(days_delta.total_seconds() + 86400))
        if invite is None:
            invite = ""

        if can_ban:
            queue_entry = (guild.id, user.id)
            await self.settings.member(user).banned_until.set(unban_time.timestamp())
            cur_tbans = await self.settings.guild(guild).current_tempbans()
            cur_tbans.append(user.id)
            await self.settings.guild(guild).current_tempbans.set(cur_tbans)

            try:  # We don't want blocked DMs preventing us from banning
                await user.send(
                    _(
                        "You have been temporarily banned from {} until {}. "
                        "Here is an invite for when your ban expires: {}"
                    ).format(guild.name, unban_time.strftime("%m-%d-%Y %H:%M:%S"), invite)
                )
            except discord.HTTPException:
                pass
            self.ban_queue.append(queue_entry)
            try:
                await guild.ban(user)
            except discord.Forbidden:
                await ctx.send(_("I can't do that for some reason."))
            except discord.HTTPException:
                await ctx.send(_("Something went wrong while banning"))
            else:
                await ctx.send(_("Done. Enough chaos for now"))

            try:
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at,
                    "tempban",
                    user,
                    author,
                    reason,
                    unban_time,
                )
            except RuntimeError as e:
                await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kicks the user, deleting 1 day worth of messages."""
        guild = ctx.guild
        channel = ctx.channel
        can_ban = channel.permissions_for(guild.me).ban_members
        author = ctx.author

        if author == user:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}")
            )
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return

        audit_reason = get_audit_reason(author, reason)

        invite = await self.get_invite_for_reinvite(ctx)
        if invite is None:
            invite = ""

        if can_ban:
            queue_entry = (guild.id, user.id)
            try:  # We don't want blocked DMs preventing us from banning
                msg = await user.send(
                    _(
                        "You have been banned and "
                        "then unbanned as a quick way to delete your messages.\n"
                        "You can now join the server again. {}"
                    ).format(invite)
                )
            except discord.HTTPException:
                msg = None
            self.ban_queue.append(queue_entry)
            try:
                await guild.ban(user, reason=audit_reason, delete_message_days=1)
            except discord.errors.Forbidden:
                self.ban_queue.remove(queue_entry)
                await ctx.send(_("My role is not high enough to softban that user."))
                if msg is not None:
                    await msg.delete()
                return
            except discord.HTTPException as e:
                self.ban_queue.remove(queue_entry)
                print(e)
                return
            self.unban_queue.append(queue_entry)
            try:
                await guild.unban(user)
            except discord.HTTPException as e:
                self.unban_queue.remove(queue_entry)
                print(e)
                return
            else:
                await ctx.send(_("Done. Enough chaos."))
                log.info(
                    "{}({}) softbanned {}({}), deleting 1 day worth "
                    "of messages".format(author.name, author.id, user.name, user.id)
                )
                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "softban",
                        user,
                        author,
                        reason,
                        until=None,
                        channel=None,
                    )
                except RuntimeError as e:
                    await ctx.send(e)
        else:
            await ctx.send(_("I'm not allowed to do that."))

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Unbans the target user.

        Requires specifying the target user's ID. To find this, you may either:
         1. Copy it from the mod log case (if one was created), or
         2. enable developer mode, go to Bans in this server's settings, right-
        click the user and select 'Copy ID'."""
        channel = ctx.channel
        if not channel.permissions_for(ctx.guild.me).ban_members:
            await ctx.send("I need the Ban Members permission to do this.")
            return
        guild = ctx.guild
        author = ctx.author
        user = await self.bot.get_user_info(user_id)
        if not user:
            await ctx.send(_("Couldn't find a user with that ID!"))
            return
        audit_reason = get_audit_reason(ctx.author, reason)
        bans = await guild.bans()
        bans = [be.user for be in bans]
        if user not in bans:
            await ctx.send(_("It seems that user isn't banned!"))
            return
        queue_entry = (guild.id, user.id)
        self.unban_queue.append(queue_entry)
        try:
            await guild.unban(user, reason=audit_reason)
        except discord.HTTPException:
            self.unban_queue.remove(queue_entry)
            await ctx.send(_("Something went wrong while attempting to unban that user"))
            return
        else:
            await ctx.send(_("Unbanned that user from this server"))

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "unban",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

        if await self.settings.guild(guild).reinvite_on_unban():
            invite = await self.get_invite_for_reinvite(ctx)
            if invite:
                try:
                    user.send(
                        _(
                            "You've been unbanned from {}.\n"
                            "Here is an invite for that server: {}"
                        ).format(guild.name, invite.url)
                    )
                except discord.Forbidden:
                    await ctx.send(
                        _(
                            "I failed to send an invite to that user. "
                            "Perhaps you may be able to send it for me?\n"
                            "Here's the invite link: {}"
                        ).format(invite.url)
                    )
                except discord.HTTPException:
                    await ctx.send(
                        _(
                            "Something went wrong when attempting to send that user"
                            "an invite. Here's the link so you can try: {}"
                        ).format(invite.url)
                    )

    @staticmethod
    async def get_invite_for_reinvite(ctx: commands.Context, max_age: int = 86400):
        """Handles the reinvite logic for getting an invite
        to send the newly unbanned user
        :returns: :class:`Invite`"""
        guild = ctx.guild
        if guild.me.permissions.manage_guild:
            if "VANITY_URL" in guild.features:
                # guild has a vanity url so use it as the one to send
                return await guild.vanity_invite()
            invites = await guild.invites()
        else:
            invites = []
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                # Invite is for the guild's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv
        else:  # No existing invite found that is valid
            channels_and_perms = zip(
                guild.text_channels, map(guild.me.permissions_in, guild.text_channels)
            )
            channel = next(
                (channel for channel, perms in channels_and_perms if perms.create_instant_invite),
                None,
            )
            if channel is None:
                return
            try:
                # Create invite that expires after max_age
                return await channel.create_invite(max_age=max_age)
            except discord.HTTPException:
                return

    @commands.command()
    @commands.guild_only()
    @admin_or_voice_permissions(mute_members=True, deafen_members=True)
    @bot_has_voice_permissions(mute_members=True, deafen_members=True)
    async def voiceban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Bans the target user from speaking and listening in voice channels in the server"""
        user_voice_state = user.voice
        if user_voice_state is None:
            await ctx.send(_("No voice state for that user!"))
            return
        needs_mute = True if user_voice_state.mute is False else False
        needs_deafen = True if user_voice_state.deaf is False else False
        audit_reason = get_audit_reason(ctx.author, reason)
        author = ctx.author
        guild = ctx.guild
        if needs_mute and needs_deafen:
            await user.edit(mute=True, deafen=True, reason=audit_reason)
        elif needs_mute:
            await user.edit(mute=True, reason=audit_reason)
        elif needs_deafen:
            await user.edit(deafen=True, reason=audit_reason)
        else:
            await ctx.send(_("That user is already muted and deafened server-wide!"))
            return
        await ctx.send(_("User has been banned from speaking or listening in voice channels"))

        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "voiceban",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @admin_or_voice_permissions(mute_members=True, deafen_members=True)
    @bot_has_voice_permissions(mute_members=True, deafen_members=True)
    async def voiceunban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Unbans the user from speaking/listening in the server's voice channels"""
        user_voice_state = user.voice
        if user_voice_state is None:
            await ctx.send(_("No voice state for that user!"))
            return
        needs_unmute = True if user_voice_state.mute else False
        needs_undeafen = True if user_voice_state.deaf else False
        audit_reason = get_audit_reason(ctx.author, reason)
        if needs_unmute and needs_undeafen:
            await user.edit(mute=False, deafen=False, reason=audit_reason)
        elif needs_unmute:
            await user.edit(mute=False, reason=audit_reason)
        elif needs_undeafen:
            await user.edit(deafen=False, reason=audit_reason)
        else:
            await ctx.send(_("That user isn't muted or deafened by the server!"))
            return
        await ctx.send(_("User is now allowed to speak and listen in voice channels"))
        guild = ctx.guild
        author = ctx.author
        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "voiceunban",
                user,
                author,
                reason,
                until=None,
                channel=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_nicknames=True)
    async def rename(self, ctx: commands.Context, user: discord.Member, *, nickname=""):
        """Changes user's nickname

        Leaving the nickname empty will remove it."""
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await user.edit(reason=get_audit_reason(ctx.author, None), nick=nickname)
            await ctx.send("Done.")
        except discord.Forbidden:
            await ctx.send(
                _("I cannot do that, I lack the '{}' permission.").format("Manage Nicknames")
            )

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channel=True)
    async def mute(self, ctx: commands.Context):
        """Mutes user in the channel/server"""
        pass

    @mute.command(name="voice", usage="<user> [-t time] [-r reason]")
    @commands.guild_only()
    @mod_or_voice_permissions(mute_members=True)
    @bot_has_voice_permissions(mute_members=True)
    async def voice_mute(
        self, ctx: commands.Context, user: discord.Member, *, args: mute_converter = (None, None)
    ):
        """Mutes the user in a voice channel
        
        You can add a reason, or make the mute temporary using arguments:

        [-t number of days, hours, minutes, seconds] [-r reason]

        [p]mute voice @AirhornSolutions -r We love the audio shitposts, but need some quiet -t 1 hour
        """
        reason, time_interval = args

        try:
            location = user.voice.channel
        except:
            location = None

        if location is None:
            return await ctx.send(_("That user is not in a voice channel right now!"))
        elif location.permissions_for(user).speak is False:
            return await ctx.send(_("That user is already muted in {}!").format(location.name))

        await self.process_mute(
            location, ctx=ctx, target=user, reason=reason, expires=time_interval, voice_mute=True
        )

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="channel", usage="<user> [-t time] [-r reason]")
    @commands.guild_only()
    async def channel_mute(
        self, ctx: commands.Context, user: discord.Member, *, args: mute_converter = (None, None)
    ):
        """Mutes user in the current channel
        
        You can add a reason, or make the mute temporary using arguments:

        [-t number of days, hours, minutes, seconds] [-r reason]

        [p]mute channel @AngryGamer -t 10 minutes -r need them on ice for a moment to mediate.
        """
        reason, time_interval = args
        await self.process_mute(
            ctx.message.channel,
            ctx=ctx,
            target=user,
            reason=reason,
            expires=time_interval,
            text_mute=True,
        )

    @checks.mod_or_permissions(administrator=True)
    @mute.command(name="server", aliases=["guild"], usage="<user> [-t time] [-r reason]")
    @commands.guild_only()
    async def guild_mute(
        self, ctx: commands.Context, user: discord.Member, *, args: mute_converter = (None, None)
    ):
        """Mutes user in the server
        
        You can add a reason, or make the mute temporary using arguments:

        [-t number of days, hours, minutes, seconds] [-r reason]

        [p]mute channel @Blaze -t 4h20m -r Won't stop talking about weed in every channel. 
        Giving them a fitting tempmute to rethink this.
        """
        reason, time_interval = args
        if time_interval is not None and time_interval.total_seconds() < 60:
            return await ctx.send(
                _("A mute this short applied server-wide will likely get me ratelimited.")
            )  # Modify handling of this to account for role based when added.
        await self.process_mute(
            *ctx.guild.channels,
            ctx=ctx,
            target=user,
            reason=reason,
            expires=time_interval,
            guild_wide=True,
        )

    async def process_mute_expiry(self, mute_dict):
        guild = self.bot.get_guild(mute_dict["guild"])
        member = guild.get_member(mute_dict["user"])
        channels = [c for c in guild.channels if c.id in mute_dict["channels"]]

        exit_codes = [
            (await self.unmute_user(guild, channel, guild.me, member)) for channel in channels
        ]

        return all(e[0] or e[1] == mute_unmute_issues["already_unmuted"] for e in exit_codes)

    async def cancel_tempmute_expires(
        self, target: discord.Member, *locations: Union[discord.TextChannel, discord.VoiceChannel]
    ):
        _tmutes = self.settings._get_base_group("TEMPMUTE")
        loc_ids = [l.id for l in locations]
        discards = set()
        async with _tmutes() as mutes:
            for eid, entry in mutes.items():
                if not entry or not entry["expiry"]:
                    # needed due to behavior with .all() on a custom group.
                    continue
                update = False
                for cid in loc_ids:
                    if cid in entry["channels"]:
                        update = bool(eid in self.scheduled_unmute_tasks)
                        entry["channels"].remove(cid)
                if update:
                    self.scheduled_unmute_tasks[eid].cancel()
                    if entry["channels"]:
                        task = self.bot.loop.create_task(
                            self._scheduled_tempexpire(
                                eid, entry, (entry["expiry"] - datetime.utcnow().timestamp())
                            )
                        )
                        self.scheduled_unmute_tasks[eid] = task
                if not entry["channels"]:
                    discards.add(eid)

            for eid in discards:
                mutes.pop(eid, None)

    async def process_mute(
        self,
        *locations: Union[discord.TextChannel, discord.VoiceChannel],
        ctx: commands.Context,
        target: discord.Member,
        reason: Optional[str] = None,
        expires: Optional[timedelta] = None,
        guild_wide: Optional[bool] = False,
        text_mute: Optional[bool] = None,
        voice_mute: Optional[bool] = None,
    ):

        reason = get_audit_reason(ctx.author, reason)
        results = {
            loc: (await self.mute_user(channel=loc, author=ctx.author, user=target, reason=reason))
            for loc in locations
        }
        messages = {k: v[1] for k, v in results.items() if v[0] is False and v[1] is not None}

        successful = {k for k, v in results.items() if v[0]}

        if successful:
            expiry = None if expires is None else (ctx.message.created_at + expires)
            if expiry:
                eid = str(ctx.message.id)
                entry = {
                    "guild": ctx.guild.id,
                    "user": target.id,
                    "expiry": expiry.timestamp(),
                    "channels": [c.id for c in successful],
                }
                await self.settings.custom("TEMPMUTE", eid).set(entry)
                if expires.total_seconds() < 600:
                    task = self.bot.loop.create_task(
                        self._scheduled_tempexpire(eid, entry, int(expires.total_seconds()))
                    )
                    self.scheduled_unmute_tasks[eid] = task
            else:
                await self.cancel_tempmute_expires(target, *successful.keys())
            await ctx.tick()

            if text_mute:
                action_type = "cmute"
            elif guild_wide:
                action_type = "smute"
            else:
                action_type = "vmute"
            await modlog.create_case(
                self.bot,
                ctx.guild,
                ctx.message.created_at,
                action_type,
                target,
                ctx.author,
                reason,
                until=expiry,
                channel=ctx.channel,
            )

        else:
            others = {k for k, m in messages.items() if m != mute_unmute_issues["already_muted"]}
            if not others:
                await ctx.send("User already muted everywhere")
            else:
                output = "I tried to mute them everywhere but failed. Ways failed below:"
                for channel, message in messages.items():
                    output += f"\n{channel.name}: {message}"
                for page in pagify(output):
                    await ctx.send(page)

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channel=True)
    async def unmute(self, ctx: commands.Context):
        """Unmutes user in the channel/server

        Defaults to channel"""
        pass

    @unmute.command(name="voice")
    @commands.guild_only()
    @mod_or_voice_permissions(mute_members=True)
    @bot_has_voice_permissions(mute_members=True)
    async def voice_unmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmutes the user in a voice channel"""
        user_voice_state = user.voice
        if user_voice_state:
            channel = user_voice_state.channel
            if channel and channel.permissions_for(user).speak is False:
                overwrites = channel.overwrites_for(user)
                overwrites.speak = None
                audit_reason = get_audit_reason(ctx.author, reason)
                await channel.set_permissions(user, overwrite=overwrites, reason=audit_reason)
                author = ctx.author
                guild = ctx.guild
                await ctx.send(
                    _("Unmuted {}#{} in channel {}").format(
                        user.name, user.discriminator, channel.name
                    )
                )
                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "vunmute",
                        user,
                        author,
                        reason,
                        until=None,
                        channel=channel,
                    )
                except RuntimeError as e:
                    await ctx.send(e)
            elif channel.permissions_for(user).speak:
                await ctx.send(_("That user is already unmuted in {}!").format(channel.name))
                return
            else:
                await ctx.send(_("That user is not in a voice channel right now!"))
        else:
            await ctx.send(_("No voice state for the target!"))
            return

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="channel")
    @commands.guild_only()
    async def channel_unmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmutes user in the current channel"""
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild

        success, message = await self.unmute_user(guild, channel, author, user)

        if success:
            await ctx.send(_("User unmuted in this channel."))
            try:
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at,
                    "cunmute",
                    user,
                    author,
                    reason,
                    until=None,
                    channel=channel,
                )
            except RuntimeError as e:
                await ctx.send(e)
        else:
            await ctx.send(_("Unmute failed. Reason: {}").format(message))

    @checks.mod_or_permissions(administrator=True)
    @unmute.command(name="server", aliases=["guild"])
    @commands.guild_only()
    async def guild_unmute(
        self, ctx: commands.Context, user: discord.Member, *, reason: str = None
    ):
        """Unmutes user in the server"""
        guild = ctx.guild
        author = ctx.author
        channel = ctx.channel

        unmute_success = []
        for channel in guild.channels:
            if not isinstance(channel, discord.TextChannel):
                if channel.permissions_for(user).speak is False:
                    overwrites = channel.overwrites_for(user)
                    overwrites.speak = None
                    audit_reason = get_audit_reason(author, reason)
                    await channel.set_permissions(user, overwrite=overwrites, reason=audit_reason)
            success, message = await self.unmute_user(guild, channel, author, user)
            unmute_success.append((success, message))
            await asyncio.sleep(0.1)
        await ctx.send(_("User has been unmuted in this server."))
        try:
            await modlog.create_case(
                self.bot,
                guild,
                ctx.message.created_at,
                "sunmute",
                user,
                author,
                reason,
                until=None,
            )
        except RuntimeError as e:
            await ctx.send(e)

    async def mute_user(
        self,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        author: discord.Member,
        user: discord.Member,
        reason: Optional[str] = None,
    ) -> (bool, str):
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)

        if isinstance(channel, discord.TextChannel):
            apply = {"send_messages": False, "add_reactions": False}
            to_cache = {
                "send_messages": overwrites.send_messages,
                "add_reactions": overwrites.add_reactions,
            }
            if (overwrites.send_messages is False or permissions.send_messages is False) and (
                overwrites.add_reactions is False or permissions.add_reactions is False
            ):
                return False, mute_unmute_issues["already_muted"]
        else:
            apply = {"speak": False}
            to_cache = {"speak": overwrites.speak}
            if overwrites.speak is False or permissions.speak is False:
                return False, mute_unmute_issues["already_muted"]

        if not await is_allowed_by_hierarchy(self.bot, self.settings, channel.guild, author, user):
            return False, mute_unmute_issues["hierarchy_problem"]

        overwrites.update(**apply)
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, mute_unmute_issues["permissions_issue"]
        else:
            async with self.settings.member(user).perms_cache() as cache:
                cache.update({str(channel.id): to_cache})
            return True, None

    async def unmute_user(
        self,
        guild: discord.Guild,
        channel: Union[discord.TextChannel, discord.VoiceChannel],
        author: discord.Member,
        user: discord.Member,
    ) -> (bool, str):
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)
        perms_cache = await self.settings.member(user).perms_cache()

        if isinstance(channel, discord.TextChannel):
            default_old_values = {"send_messages": None, "add_reactions": None}
            if overwrites.send_messages or permissions.send_messages:
                return False, mute_unmute_issues["already_unmuted"]
        else:
            default_old_values = {"speak": None}
            if overwrites.speak or permissions.speak:
                return False, mute_unmute_issues["already_unmuted"]

        if not await is_allowed_by_hierarchy(self.bot, self.settings, channel.guild, author, user):
            return False, mute_unmute_issues["hierarchy_problem"]

        if channel.id in perms_cache:
            old_values = perms_cache[channel.id]
        else:
            old_values = default_old_values
        overwrites.update(**old_values)
        is_empty = self.are_overwrites_empty(overwrites)

        try:
            if not is_empty:
                await channel.set_permissions(user, overwrite=overwrites)
            else:
                await channel.set_permissions(user, overwrite=None)
        except discord.Forbidden:
            return False, mute_unmute_issues["permissions_issue"]
        else:
            try:
                del perms_cache[channel.id]
            except KeyError:
                pass
            else:
                await self.settings.member(user).perms_cache.set(perms_cache)
            return True, None

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def ignore(self, ctx: commands.Context):
        """Adds servers/channels to ignorelist"""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.count_ignored())

    @ignore.command(name="channel")
    async def ignore_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Ignores channel

        Defaults to current one"""
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
        """Ignores current server"""
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
        """Removes servers/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.count_ignored())

    @unignore.command(name="channel")
    async def unignore_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """Removes channel from ignore list

        Defaults to current one"""
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
        """Removes current guild from ignore list"""
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
        surpass the check."""
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

    @commands.command()
    @commands.guild_only()
    async def userinfo(self, ctx, *, user: discord.Member = None):
        """Shows information for a user.
        
        This includes fields for status, discord join date, server
        join date, voice state and previous names/nicknames.
        
        If the user has none of roles, previous names or previous
        nicknames, these fields will be omitted.
        """
        author = ctx.author
        guild = ctx.guild

        if not user:
            user = author

        #  A special case for a special someone :^)
        special_date = datetime(2016, 1, 10, 6, 8, 4, 443000)
        is_special = user.id == 96130341705637888 and guild.id == 133049272517001216

        roles = sorted(user.roles)[1:]
        names, nicks = await self.get_names_and_nicks(user)

        joined_at = user.joined_at if not is_special else special_date
        since_created = (ctx.message.created_at - user.created_at).days
        since_joined = (ctx.message.created_at - joined_at).days
        user_joined = joined_at.strftime("%d %b %Y %H:%M")
        user_created = user.created_at.strftime("%d %b %Y %H:%M")
        voice_state = user.voice
        member_number = sorted(guild.members, key=lambda m: m.joined_at).index(user) + 1

        created_on = _("{}\n({} days ago)").format(user_created, since_created)
        joined_on = _("{}\n({} days ago)").format(user_joined, since_joined)

        activity = _("Chilling in {} status").format(user.status)
        if user.activity is None:  # Default status
            pass
        elif user.activity.type == discord.ActivityType.playing:
            activity = _("Playing {}").format(user.activity.name)
        elif user.activity.type == discord.ActivityType.streaming:
            activity = _("Streaming [{}]({})").format(user.activity.name, user.activity.url)
        elif user.activity.type == discord.ActivityType.listening:
            activity = _("Listening to {}").format(user.activity.name)
        elif user.activity.type == discord.ActivityType.watching:
            activity = _("Watching {}").format(user.activity.name)

        if roles:
            roles = ", ".join([x.name for x in roles])
        else:
            roles = None

        data = discord.Embed(description=activity, colour=user.colour)
        data.add_field(name=_("Joined Discord on"), value=created_on)
        data.add_field(name=_("Joined this server on"), value=joined_on)
        if roles is not None:
            data.add_field(name=_("Roles"), value=roles, inline=False)
        if names:
            # May need sanitizing later, but mentions do not ping in embeds currently
            val = filter_invites(", ".join(names))
            data.add_field(name=_("Previous Names"), value=val, inline=False)
        if nicks:
            # May need sanitizing later, but mentions do not ping in embeds currently
            val = filter_invites(", ".join(nicks))
            data.add_field(name=_("Previous Nicknames"), value=val, inline=False)
        if voice_state and voice_state.channel:
            data.add_field(
                name=_("Current voice channel"),
                value="{0.name} (ID {0.id})".format(voice_state.channel),
                inline=False,
            )
        data.set_footer(text=_("Member #{} | User ID: {}").format(member_number, user.id))

        name = str(user)
        name = " ~ ".join((name, user.nick)) if user.nick else name
        name = filter_invites(name)

        if user.avatar:
            avatar = user.avatar_url
            avatar = avatar.replace("webp", "png")
            data.set_author(name=name, url=avatar)
            data.set_thumbnail(url=avatar)
        else:
            data.set_author(name=name)

        try:
            await ctx.send(embed=data)
        except discord.HTTPException:
            await ctx.send(_("I need the `Embed links` permission to send this."))

    @commands.command()
    async def names(self, ctx: commands.Context, user: discord.Member):
        """Show previous names/nicknames of a user"""
        names, nicks = await self.get_names_and_nicks(user)
        msg = ""
        if names:
            msg += _("**Past 20 names**:")
            msg += "\n"
            msg += ", ".join(names)
        if nicks:
            if msg:
                msg += "\n\n"
            msg += _("**Past 20 nicknames**:")
            msg += "\n"
            msg += ", ".join(nicks)
        if msg:
            msg = filter_various_mentions(msg)
            await ctx.send(msg)
        else:
            await ctx.send(_("That user doesn't have any recorded name or nickname change."))

    async def get_names_and_nicks(self, user):
        names = await self.settings.user(user).past_names()
        nicks = await self.settings.member(user).past_nicks()
        if names:
            names = [escape(name, mass_mentions=True) for name in names if name]
        if nicks:
            nicks = [escape(nick, mass_mentions=True) for nick in nicks if nick]
        return names, nicks

    async def _scheduled_tempexpire(self, eid, entry, delay):
        await asyncio.sleep(delay)
        try:
            if await self.process_mute_expiry(entry):
                data = await self.settings._get_base_group("TEMPMUTE").all()
                data.pop(eid, None)
                await self.settings._get_base_group("TEMPMUTE").set(data)
            else:
                log.info("Failed to revoke a tempban in guild with id: %d", entry["guild"])
        except (AttributeError, KeyError):
            pass
            # Can't find guild or member anymore,
            # not safe to remove, possible API unavailable

    async def check_tempmute_expirations(self):
        _tmutes = self.settings._get_base_group("TEMPMUTE")
        while self == self.bot.get_cog("Mod"):
            temp_mutes = await _tmutes.all()
            for eid, entry in temp_mutes.items():
                if not entry or not entry["expiry"]:
                    # needed due to behavior with .all() on a custom group.
                    continue
                delay = max(0, (entry["expiry"] - datetime.utcnow().timestamp()))
                if delay < 200 and eid not in self.scheduled_unmute_tasks:
                    eid_unmute = self.bot.loop.create_task(
                        self._scheduled_tempexpire(eid, entry, delay)
                    )
                    self.scheduled_unmute_tasks[eid] = eid_unmute
            await asyncio.sleep(300)
            self.scheduled_unmute_tasks = {
                k: v for k, v in self.scheduled_unmute_tasks.items() if not v.done()
            }

    async def check_tempban_expirations(self):
        member = namedtuple("Member", "id guild")
        while self == self.bot.get_cog("Mod"):
            for guild in self.bot.guilds:
                async with self.settings.guild(guild).current_tempbans() as guild_tempbans:
                    for uid in guild_tempbans:
                        unban_time = datetime.utcfromtimestamp(
                            await self.settings.member(member(uid, guild)).banned_until()
                        )
                        now = datetime.utcnow()
                        if now > unban_time:  # Time to unban the user
                            user = await self.bot.get_user_info(uid)
                            queue_entry = (guild.id, user.id)
                            self.unban_queue.append(queue_entry)
                            try:
                                await guild.unban(user, reason="Tempban finished")
                                guild_tempbans.remove(uid)
                            except discord.Forbidden:
                                self.unban_queue.remove(queue_entry)
                                log.info("Failed to unban member due to permissions")
                            except discord.HTTPException:
                                self.unban_queue.remove(queue_entry)
            await asyncio.sleep(60)

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

        if await self.settings.guild(guild).ban_mention_spam():
            max_mentions = await self.settings.guild(guild).ban_mention_spam()
            mentions = set(message.mentions)
            if len(mentions) >= max_mentions:
                try:
                    await guild.ban(author, reason="Mention spam (Autoban)")
                except discord.HTTPException:
                    log.info(
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
                            "Mention spam (Autoban)",
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
            try:
                await m.delete()
                log.debug("Deleted command msg {}".format(m.id))
            except:
                pass  # We don't really care if it fails or not

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
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if mod_or_superior:
            return
        # As are anyone configured to be
        if await self.bot.is_automod_immune(message):
            return
        deleted = await self.check_duplicates(message)
        if not deleted:
            deleted = await self.check_mention_spam(message)

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

    async def on_modlog_case_create(self, case: modlog.Case):
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

    async def on_modlog_case_edit(self, case: modlog.Case):
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

    async def get_audit_entry_info(self, guild: discord.Guild, action: int, target):
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
            entry = await self.get_audit_log_entry(guild, action=action, target=target)
        except discord.HTTPException:
            entry = None
        if entry is None:
            return None, None, None
        return entry.user, entry.reason, entry.created_at

    async def get_audit_log_entry(self, guild: discord.Guild, action: int, target):
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

    @staticmethod
    def are_overwrites_empty(overwrites):
        """There is currently no cleaner way to check if a
        PermissionOverwrite object is empty"""
        return [p for p in iter(overwrites)] == [p for p in iter(discord.PermissionOverwrite())]


mute_unmute_issues = {
    "already_muted": "That user can't send messages in this channel.",
    "already_unmuted": "That user isn't muted in this channel!",
    "hierarchy_problem": "I cannot let you do that. You are not higher than "
    "the user in the role hierarchy.",
    "permissions_issue": "Failed to mute user. I need the manage roles "
    "permission and the user I'm muting must be "
    "lower than myself in the role hierarchy.",
}
