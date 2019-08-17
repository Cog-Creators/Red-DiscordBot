import asyncio
import contextlib
import logging
from collections import namedtuple
from datetime import datetime, timedelta
from typing import cast, Optional, Union

import discord
from redbot.core import commands, i18n, checks, modlog
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.mod import is_allowed_by_hierarchy, get_audit_reason
from .abc import MixinMeta
from .converters import RawUserIds

log = logging.getLogger("red.mod")
_ = i18n.Translator("Mod", __file__)


class KickBanMixin(MixinMeta):
    """
    Kick and ban commands and tasks go here.
    """

    @staticmethod
    async def get_invite_for_reinvite(ctx: commands.Context, max_age: int = 86400):
        """Handles the reinvite logic for getting an invite
        to send the newly unbanned user
        :returns: :class:`Invite`"""
        guild = ctx.guild
        my_perms: discord.Permissions = guild.me.guild_permissions
        if my_perms.manage_guild or my_perms.administrator:
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

    async def ban_user(
        self,
        user: discord.Member,
        ctx: commands.Context,
        days: int = 0,
        reason: str = None,
        create_modlog_case=False,
    ) -> Union[str, bool]:
        author = ctx.author
        guild = ctx.guild

        if author == user:
            return _("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}")
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            return _(
                "I cannot let you do that. You are "
                "not higher than the user in the role "
                "hierarchy."
            )
        elif guild.me.top_role <= user.top_role or user == guild.owner:
            return _("I cannot do that due to discord hierarchy rules")
        elif not (0 <= days <= 7):
            return _("Invalid days. Must be between 0 and 7.")

        audit_reason = get_audit_reason(author, reason)

        queue_entry = (guild.id, user.id)
        try:
            await guild.ban(user, reason=audit_reason, delete_message_days=days)
            log.info(
                "{}({}) banned {}({}), deleting {} days worth of messages".format(
                    author.name, author.id, user.name, user.id, str(days)
                )
            )
        except discord.Forbidden:
            return _("I'm not allowed to do that.")
        except Exception as e:
            return e  # TODO: impproper return type? Is this intended to be re-raised?

        if create_modlog_case:
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
                return _(
                    "The user was banned but an error occurred when trying to "
                    "create the modlog entry: {reason}"
                ).format(reason=e)

        return True

    async def check_tempban_expirations(self):
        member = namedtuple("Member", "id guild")
        while self == self.bot.get_cog("Mod"):
            for guild in self.bot.guilds:
                async with self.settings.guild(guild).current_tempbans() as guild_tempbans:
                    for uid in guild_tempbans.copy():
                        unban_time = datetime.utcfromtimestamp(
                            await self.settings.member(member(uid, guild)).banned_until()
                        )
                        now = datetime.utcnow()
                        if now > unban_time:  # Time to unban the user
                            user = await self.bot.fetch_user(uid)
                            queue_entry = (guild.id, user.id)
                            try:
                                await guild.unban(user, reason=_("Tempban finished"))
                                guild_tempbans.remove(uid)
                            except discord.Forbidden:
                                log.info("Failed to unban member due to permissions")
                            except discord.HTTPException as e:
                                log.info(f"Failed to unban member: error code: {e.code}")
            await asyncio.sleep(60)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    @checks.admin_or_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kick a user.

        If a reason is specified, it will be the reason that shows up
        in the audit log.
        """
        author = ctx.author
        guild = ctx.guild

        if author == user:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {emoji}").format(
                    emoji="\N{PENSIVE FACE}"
                )
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
            await ctx.send(_("Done. That felt good."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        user: discord.Member,
        days: Optional[int] = 0,
        *,
        reason: str = None,
    ):
        """Ban a user from this server and optionally delete days of messages.

        If days is not a number, it's treated as the first word of the reason.
        Minimum 0 days, maximum 7. Defaults to 0."""

        result = await self.ban_user(
            user=user, ctx=ctx, days=days, reason=reason, create_modlog_case=True
        )

        if result is True:
            await ctx.send(_("Done. It was about time."))
        elif isinstance(result, str):
            await ctx.send(result)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def hackban(
        self,
        ctx: commands.Context,
        user_ids: commands.Greedy[RawUserIds],
        days: Optional[int] = 0,
        *,
        reason: str = None,
    ):
        """Preemptively bans user(s) from the server

        User IDs need to be provided in order to ban
        using this command"""
        days = cast(int, days)
        banned = []
        errors = {}

        async def show_results():
            text = _("Banned {num} users from the server.").format(num=len(banned))
            if errors:
                text += _("\nErrors:\n")
                text += "\n".join(errors.values())

            for p in pagify(text):
                await ctx.send(p)

        def remove_processed(ids):
            return [_id for _id in ids if _id not in banned and _id not in errors]

        user_ids = list(set(user_ids))  # No dupes

        author = ctx.author
        guild = ctx.guild

        if not user_ids:
            await ctx.send_help()
            return

        if not (0 <= days <= 7):
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return

        if not guild.me.guild_permissions.ban_members:
            return await ctx.send(_("I lack the permissions to do this."))

        ban_list = await guild.bans()
        for entry in ban_list:
            for user_id in user_ids:
                if entry.user.id == user_id:
                    errors[user_id] = _("User {user_id} is already banned.").format(
                        user_id=user_id
                    )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        for user_id in user_ids:
            user = guild.get_member(user_id)
            if user is not None:
                # Instead of replicating all that handling... gets attr from decorator
                try:
                    result = await self.ban_user(
                        user=user, ctx=ctx, days=days, reason=reason, create_modlog_case=True
                    )
                    if result is True:
                        banned.append(user_id)
                    else:
                        errors[user_id] = _("Failed to ban user {user_id}: {reason}").format(
                            user_id=user_id, reason=result
                        )
                except Exception as e:
                    errors[user_id] = _("Failed to ban user {user_id}: {reason}").format(
                        user_id=user_id, reason=e
                    )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        for user_id in user_ids:
            user = discord.Object(id=user_id)
            audit_reason = get_audit_reason(author, reason)
            queue_entry = (guild.id, user_id)
            try:
                await guild.ban(user, reason=audit_reason, delete_message_days=days)
                log.info("{}({}) hackbanned {}".format(author.name, author.id, user_id))
            except discord.NotFound:
                errors[user_id] = _("User {user_id} does not exist.").format(user_id=user_id)
                continue
            except discord.Forbidden:
                errors[user_id] = _("Could not ban {user_id}: missing permissions.").format(
                    user_id=user_id
                )
                continue
            else:
                banned.append(user_id)

            user_info = await self.bot.fetch_user(user_id)

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
                errors["0"] = _("Failed to create modlog case: {reason}").format(reason=e)
        await show_results()

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def tempban(
        self, ctx: commands.Context, user: discord.Member, days: int = 1, *, reason: str = None
    ):
        """Temporarily ban a user from this server."""
        guild = ctx.guild
        author = ctx.author
        days_delta = timedelta(days=int(days))
        unban_time = datetime.utcnow() + days_delta

        invite = await self.get_invite_for_reinvite(ctx, int(days_delta.total_seconds() + 86400))
        if invite is None:
            invite = ""

        queue_entry = (guild.id, user.id)
        await self.settings.member(user).banned_until.set(unban_time.timestamp())
        cur_tbans = await self.settings.guild(guild).current_tempbans()
        cur_tbans.append(user.id)
        await self.settings.guild(guild).current_tempbans.set(cur_tbans)

        with contextlib.suppress(discord.HTTPException):
            # We don't want blocked DMs preventing us from banning
            await user.send(
                _(
                    "You have been temporarily banned from {server_name} until {date}. "
                    "Here is an invite for when your ban expires: {invite_link}"
                ).format(
                    server_name=guild.name,
                    date=unban_time.strftime("%m-%d-%Y %H:%M:%S"),
                    invite_link=invite,
                )
            )
        try:
            await guild.ban(user)
        except discord.Forbidden:
            await ctx.send(_("I can't do that for some reason."))
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while banning"))
        else:
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
            await ctx.send(_("Done. Enough chaos for now"))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def softban(self, ctx: commands.Context, user: discord.Member, *, reason: str = None):
        """Kick a user and delete 1 day's worth of their messages."""
        guild = ctx.guild
        author = ctx.author

        if author == user:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {emoji}").format(
                    emoji="\N{PENSIVE FACE}"
                )
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

        queue_entry = (guild.id, user.id)
        try:  # We don't want blocked DMs preventing us from banning
            msg = await user.send(
                _(
                    "You have been banned and "
                    "then unbanned as a quick way to delete your messages.\n"
                    "You can now join the server again. {invite_link}"
                ).format(invite_link=invite)
            )
        except discord.HTTPException:
            msg = None
        try:
            await guild.ban(user, reason=audit_reason, delete_message_days=1)
        except discord.errors.Forbidden:
            await ctx.send(_("My role is not high enough to softban that user."))
            if msg is not None:
                await msg.delete()
            return
        except discord.HTTPException as e:
            print(e)
            return
        try:
            await guild.unban(user)
        except discord.HTTPException as e:
            print(e)
            return
        else:
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
            await ctx.send(_("Done. Enough chaos."))

    @commands.command()
    @commands.guild_only()
    @commands.mod_or_permissions(move_members=True)
    async def voicekick(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Kick a member from a voice channel."""
        author = ctx.author
        guild = ctx.guild
        user_voice_state: discord.VoiceState = member.voice

        if await self._voice_perm_check(ctx, user_voice_state, move_members=True) is False:
            return
        elif not await is_allowed_by_hierarchy(self.bot, self.settings, guild, author, member):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        case_channel = member.voice.channel
        # Store this channel for the case channel.

        try:
            await member.move_to(discord.Object(id=None))
            # Work around till we get D.py 1.1.0, whereby we can directly do None.
        except discord.Forbidden:  # Very unlikely that this will ever occur
            await ctx.send(_("I am unable to kick this member from the voice channel."))
            return
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while attempting to kick that member"))
            return
        else:
            try:
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at,
                    "vkick",
                    member,
                    author,
                    reason,
                    until=None,
                    channel=case_channel,
                )
            except RuntimeError as e:
                await ctx.send(e)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Unban a user from this server.

        Requires specifying the target user's ID. To find this, you may either:
         1. Copy it from the mod log case (if one was created), or
         2. enable developer mode, go to Bans in this server's settings, right-
        click the user and select 'Copy ID'."""
        guild = ctx.guild
        author = ctx.author
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.errors.NotFound:
            await ctx.send(_("Couldn't find a user with that ID!"))
            return
        audit_reason = get_audit_reason(ctx.author, reason)
        bans = await guild.bans()
        bans = [be.user for be in bans]
        if user not in bans:
            await ctx.send(_("It seems that user isn't banned!"))
            return
        queue_entry = (guild.id, user.id)
        try:
            await guild.unban(user, reason=audit_reason)
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while attempting to unban that user"))
            return
        else:
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
            await ctx.send(_("Unbanned that user from this server"))

        if await self.settings.guild(guild).reinvite_on_unban():
            invite = await self.get_invite_for_reinvite(ctx)
            if invite:
                try:
                    await user.send(
                        _(
                            "You've been unbanned from {server}.\n"
                            "Here is an invite for that server: {invite_link}"
                        ).format(server=guild.name, invite_link=invite.url)
                    )
                except discord.Forbidden:
                    await ctx.send(
                        _(
                            "I failed to send an invite to that user. "
                            "Perhaps you may be able to send it for me?\n"
                            "Here's the invite link: {invite_link}"
                        ).format(invite_link=invite.url)
                    )
                except discord.HTTPException:
                    await ctx.send(
                        _(
                            "Something went wrong when attempting to send that user"
                            "an invite. Here's the link so you can try: {invite_link}"
                        ).format(invite_link=invite.url)
                    )
