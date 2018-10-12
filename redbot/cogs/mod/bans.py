import asyncio
import contextlib
from collections import namedtuple
from datetime import datetime, timedelta

import discord
from redbot.core import checks, modlog, commands
from redbot.core.bot import Red
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, escape

_ = T_ = Translator("Mod", __file__)


class KickBanMixin:
    """
    Handles Ban related actions for Mod cog
    """

    def __init__(self):
        self.ban_queue = []
        self.unban_queue = []
        self.tban_expiry_task = self.bot.loop.create_task(self.check_tempban_expirations())
        super().__init__()

    def __unload(self):
        self.tban_expiry_task.cancel()

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
                            user = await self.bot.get_user_info(uid)
                            queue_entry = (guild.id, user.id)
                            self.unban_queue.append(queue_entry)
                            try:
                                await guild.unban(user, reason=_("Tempban finished"))
                                guild_tempbans.remove(uid)
                            except discord.Forbidden:
                                self.unban_queue.remove(queue_entry)
                                self.log.info("Failed to unban member due to permissions")
                            except discord.HTTPException:
                                self.unban_queue.remove(queue_entry)
            await asyncio.sleep(60)

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
        elif not await self.is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
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
        audit_reason = self.get_audit_reason(author, reason)
        try:
            await guild.kick(user, reason=audit_reason)
            self.log.info(
                "{}({}) kicked {}({})".format(author.name, author.id, user.name, user.id)
            )
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
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def ban(
        self, ctx: commands.Context, user: discord.Member, days: str = None, *, reason: str = None
    ):
        """Ban a user from this server.

        Deletes `<days>` worth of messages.

        If `<days>` is not a number, it's treated as the first word of
        the reason.  Minimum 0 days, maximum 7. Defaults to 0.
        """
        author = ctx.author
        guild = ctx.guild

        if author == user:
            await ctx.send(
                _("I cannot let you do that. Self-harm is bad {}").format("\N{PENSIVE FACE}")
            )
            return
        elif not await self.is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
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

        audit_reason = self.get_audit_reason(author, reason)

        if days < 0 or days > 7:
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return
        queue_entry = (guild.id, user.id)
        self.ban_queue.append(queue_entry)
        try:
            await guild.ban(user, reason=audit_reason, delete_message_days=days)
            self.log.info(
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
    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    async def hackban(self, ctx: commands.Context, user_id: int, *, reason: str = None):
        """Pre-emptively ban a user from this server.

        A user ID needs to be provided in order to ban
        using this command.
        """
        author = ctx.author
        guild = ctx.guild
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

        audit_reason = self.get_audit_reason(author, reason)
        queue_entry = (guild.id, user_id)
        self.ban_queue.append(queue_entry)
        try:
            await guild.ban(user, reason=audit_reason)
            self.log.info("{}({}) hackbanned {}".format(author.name, author.id, user_id))
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
        elif not await self.is_allowed_by_hierarchy(self.bot, self.settings, guild, author, user):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return

        audit_reason = self.get_audit_reason(author, reason)

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
            self.log.info(
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
        user = await self.bot.get_user_info(user_id)
        if not user:
            await ctx.send(_("Couldn't find a user with that ID!"))
            return
        audit_reason = self.get_audit_reason(ctx.author, reason)
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
