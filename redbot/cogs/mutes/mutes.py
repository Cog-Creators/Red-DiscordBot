import asyncio
import contextlib
import discord
import logging

from abc import ABC
from typing import Optional, List, Literal, Union, Tuple
from datetime import datetime, timedelta, timezone

from .converters import MuteTime
from .voicemutes import VoiceMutes

from redbot.core.bot import Red
from redbot.core import commands, checks, i18n, modlog, mutes
from redbot.core.errors import MuteError
from redbot.core.utils import bounded_gather
from redbot.core.utils.chat_formatting import bold, humanize_timedelta, humanize_list, pagify
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

T_ = i18n.Translator("Mutes", __file__)

_ = lambda s: s

MUTE_UNMUTE_ISSUES = {
    mutes.MuteUnmuteIssue.ALREADY_MUTED: _("That user is already muted in this channel."),
    mutes.MuteUnmuteIssue.ALREADY_UNMUTED: _("That user is not muted in this channel."),
    mutes.MuteUnmuteIssue.HIERARCHY_PROBLEM: _(
        "I cannot let you do that. You are not higher than the user in the role hierarchy."
    ),
    mutes.MuteUnmuteIssue.ASSIGNED_ROLE_HIERARCHY_PROBLEM: _(
        "I cannot let you do that. You are not higher than the mute role in the role hierarchy."
    ),
    mutes.MuteUnmuteIssue.IS_ADMIN: _(
        "That user cannot be (un)muted, as they have the Administrator permission."
    ),
    mutes.MuteUnmuteIssue.PERMISSIONS_ISSUE_ROLE: _(
        "Failed to mute or unmute user. I need the Manage Roles "
        "permission and the user I'm muting must be "
        "lower than myself in the role hierarchy."
    ),
    mutes.MuteUnmuteIssue.PERMISSIONS_ISSUE_CHANNEL: _(
        "Failed to mute or unmute user. I need the Manage Permissions permission."
    ),
    mutes.MuteUnmuteIssue.LEFT_GUILD: _(
        "The user has left the server while applying an overwrite."
    ),
    mutes.MuteUnmuteIssue.UNKNONW_CHANNEL: _(
        "The channel I tried to mute or unmute the user in isn't found."
    ),
    mutes.MuteUnmuteIssue.ROLE_MISSING: _("The mute role no longer exists."),
    mutes.MuteUnmuteIssue.VOICE_MUTE_PERMISSION: _(
        "Because I don't have the Move Members permission, this will take into "
        "effect when the user rejoins."
    ),
}

_ = T_

log = logging.getLogger("red.cogs.mutes")

__version__ = "1.0.0"


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


@i18n.cog_i18n(_)
class Mutes(VoiceMutes, commands.Cog, metaclass=CompositeMetaClass):
    """
    Mute users temporarily or indefinitely.
    """

    def __init__(self, bot: Red):
        self.bot = bot

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """Mutes are considered somewhat critical
        Therefore the only data that we should delete
        is that which comes from discord requesting us to
        remove data about a user
        """
        if requester != "discord_deleted_user":
            return

        await self._ready.wait()
        all_members = await self.config.all_members()
        for g_id, data in all_members.items():
            for m_id, user_mute in data.items():
                if m_id == user_id:
                    await self.config.member_from_ids(g_id, m_id).clear()

    async def cog_before_invoke(self, ctx: commands.Context):
        # wait until cores mutes logic is ready
        await mutes.wait_for_mutes(self.bot)

    @commands.group()
    @commands.guild_only()
    async def muteset(self, ctx: commands.Context):
        """Mute settings."""
        pass

    @muteset.command(name="disable")
    @commands.is_owner()
    async def disable_mutes(self, ctx: commands.Context, true_or_false: bool):
        """
        Set whether or not mutes will be disabled

        `<true_or_false>` Either `true` or `false` whether mutes should
        be disabled.
        """
        if true_or_false:
            await self.bot._mutes.config.disabled.set(true_or_false)
            return await ctx.send(
                _("Mutes is now disabled and any cogs utilizing the API will not work.")
            )
        else:
            await self.bot._mutes.config.clear()
            await ctx.send(_("Mutes API is now enabled."))

    @muteset.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def senddm(self, ctx: commands.Context, true_or_false: bool):
        """Set whether mute notifications should be sent to users in DMs."""
        await self.config.guild(ctx.guild).dm.set(true_or_false)
        if true_or_false:
            await ctx.send(_("I will now try to send mute notifications to users DMs."))
        else:
            await ctx.send(_("Mute notifications will no longer be sent to users DMs."))

    @muteset.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_channels=True)
    async def showmoderator(self, ctx, true_or_false: bool):
        """
        Decide whether the name of the moderator muting a user
        should be included in the DM to that user.
        """
        await self.config.guild(ctx.guild).show_mod.set(true_or_false)
        if true_or_false:
            await ctx.send(
                _(
                    "I will include the name of the moderator who issued the "
                    "mute when sending a DM to a user."
                )
            )
        else:
            await ctx.send(
                _(
                    "I will not include the name of the moderator who issued the "
                    "mute when sending a DM to a user."
                )
            )

    @muteset.command(name="forcerole")
    @commands.is_owner()
    async def force_role_mutes(self, ctx: commands.Context, force_role_mutes: bool):
        """
        Whether or not to force role only mutes on the bot
        """
        await self.config.force_role_mutes.set(force_role_mutes)
        if force_role_mutes:
            await ctx.send(_("Okay I will enforce role mutes before muting users."))
        else:
            await ctx.send(_("Okay I will allow channel overwrites for muting users."))

    @muteset.command(name="settings", aliases=["showsettings"])
    @checks.mod_or_permissions(manage_channels=True)
    async def show_mutes_settings(self, ctx: commands.Context):
        """
        Shows the current mute settings for this guild.
        """
        data = await self.config.guild(ctx.guild).all()

        mute_role = ctx.guild.get_role(data["mute_role"])
        notification_channel = ctx.guild.get_channel(data["notification_channel"])
        default_time = timedelta(seconds=data["default_time"])
        msg = _(
            "Mute Role: {role}\n"
            "Notification Channel: {channel}\n"
            "Default Time: {time}\n"
            "Send DM: {dm}\n"
            "Show moderator: {show_mod}"
        ).format(
            role=mute_role.mention if mute_role else _("None"),
            channel=notification_channel.mention if notification_channel else _("None"),
            time=humanize_timedelta(timedelta=default_time) if default_time else _("None"),
            dm=data["dm"],
            show_mod=data["show_mod"],
        )
        await ctx.maybe_send_embed(msg)

    @muteset.command(name="notification")
    @checks.admin_or_permissions(manage_channels=True)
    async def notification_channel_set(
        self, ctx: commands.Context, channel: Optional[discord.TextChannel] = None
    ):
        """
        Set the notification channel for automatic unmute issues.

        If no channel is provided this will be cleared and notifications
        about issues when unmuting users will not be sent anywhere.
        """
        await mutes.set_mute_notification_channel(self.bot, ctx.guild, channel)
        if channel is None:
            await ctx.send(_("Notification channel for unmute issues has been cleared."))
        else:
            await ctx.send(
                _("I will post unmute issues in {channel}.").format(channel=channel.mention)
            )

    @muteset.command(name="role")
    @checks.admin_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def mute_role(self, ctx: commands.Context, *, role: discord.Role = None):
        """Sets the role to be applied when muting a user.

        If no role is setup the bot will attempt to mute a user by setting
        channel overwrites in all channels to prevent the user from sending messages.

        Note: If no role is setup a user may be able to leave the server
        and rejoin no longer being muted.
        """
        if not role:
            await mutes.set_mute_role(self.bot, ctx.guild, role)
            # reset this to warn users next time they may have accidentally
            # removed the mute role
            await ctx.send(_("Channel overwrites will be used for mutes instead."))
        else:
            if role >= ctx.author.top_role:
                await ctx.send(
                    _("You can't set this role as it is not lower than you in the role hierarchy.")
                )
                return
            await mutes.set_mute_role(self.bot, ctx.guild, role)
            await ctx.send(_("Mute role set to {role}").format(role=role.name))
        if not await mutes.get_mute_notification_channel(self.bot, ctx.guild):
            command_1 = f"`{ctx.clean_prefix}muteset notification`"
            await ctx.send(
                _(
                    "No notification channel has been setup, "
                    "use {command_1} to be updated when there's an issue in automatic unmutes."
                ).format(command_1=command_1)
            )

    @muteset.command(name="makerole")
    @checks.admin_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.max_concurrency(1, commands.BucketType.guild)
    async def make_mute_role(self, ctx: commands.Context, *, name: str):
        """Create a Muted role.

        This will create a role and apply overwrites to all available channels
        to more easily setup muting a user.

        If you already have a muted role created on the server use
        `[p]muteset role ROLE_NAME_HERE`
        """
        if await mutes.get_mute_role(ctx.guild):
            command = f"`{ctx.clean_prefix}muteset role`"
            return await ctx.send(
                _(
                    "There is already a mute role setup in this server. "
                    "Please remove it with {command} before trying to "
                    "create a new one."
                ).format(command=command)
            )
        async with ctx.typing():
            perms = discord.Permissions()
            perms.update(send_messages=False, speak=False, add_reactions=False)
            try:
                role = await ctx.guild.create_role(
                    name=name, permissions=perms, reason=_("Mute role setup")
                )
                await mutes.set_mute_role(self.bot, ctx.guild, role)
                # save the role early incase of issue later
            except discord.errors.Forbidden:
                return await ctx.send(_("I could not create a muted role in this server."))
            errors = []
            tasks = []
            for channel in ctx.guild.channels:
                tasks.append(self._set_mute_role_overwrites(role, channel))
            errors = await bounded_gather(*tasks)
            if any(errors):
                msg = _(
                    "I could not set overwrites for the following channels: {channels}"
                ).format(channels=humanize_list([i for i in errors if i]))
                for page in pagify(msg, delims=[" "]):
                    await ctx.send(page)

            await ctx.send(_("Mute role set to {role}").format(role=role.name))
        if not await mutes.get_mute_notification_channel(self.bot, ctx.guild):
            command_1 = f"`{ctx.clean_prefix}muteset notification`"
            await ctx.send(
                _(
                    "No notification channel has been setup, "
                    "use {command_1} to be updated when there's an issue in automatic unmutes."
                ).format(command_1=command_1)
            )

    async def _set_mute_role_overwrites(
        self, role: discord.Role, channel: discord.abc.GuildChannel
    ) -> Optional[str]:
        """
        This sets the supplied role and channel overwrites to what we want
        by default for a mute role
        """
        if not channel.permissions_for(channel.guild.me).manage_permissions:
            return channel.mention
        overs = discord.PermissionOverwrite()
        overs.send_messages = False
        overs.add_reactions = False
        overs.speak = False
        try:
            await channel.set_permissions(role, overwrite=overs, reason=_("Mute role setup"))
            return None
        except discord.errors.Forbidden:
            return channel.mention

    @muteset.command(name="defaulttime", aliases=["time"])
    @checks.mod_or_permissions(manage_messages=True)
    async def default_mute_time(self, ctx: commands.Context, *, time: Optional[MuteTime] = None):
        """
        Set the default mute time for the mute command.

        If no time interval is provided this will be cleared.
        """

        if not time:
            await self.config.guild(ctx.guild).default_time.clear()
            await ctx.send(_("Default mute time removed."))
        else:
            data = time.get("duration", {})
            if not data:
                return await ctx.send(_("Please provide a valid time format."))
            await self.config.guild(ctx.guild).default_time.set(data.total_seconds())
            await ctx.send(
                _("Default mute time set to {time}.").format(
                    time=humanize_timedelta(timedelta=data)
                )
            )

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def activemutes(self, ctx: commands.Context):
        """
        Displays active mutes on this server.
        """
        msg = ""
        server_mutes = {}
        channel_mutes = {}
        try:
            server_mutes = mutes.get_active_guild_mutes(self.bot, ctx.guild)
        except KeyError:
            pass
        try:
            channel_mutes = mutes.get_active_channel_mutes(self.bot, ctx.guild)
        except KeyError:
            pass
        if not server_mutes and not channel_mutes:
            return await ctx.maybe_send_embed(_("There are no mutes on this server right now."))
        if server_mutes:

            msg += _("__Server Mutes__\n")
            for user_id, muted_user in server_mutes.items():
                if not muted_user:
                    continue
                user = ctx.guild.get_member(user_id)
                if not user:
                    user_str = f"<@!{user_id}>"
                else:
                    user_str = user.mention
                if muted_user.until:
                    time_left = timedelta(
                        seconds=muted_user.until - datetime.now(timezone.utc).timestamp()
                    )
                    time_str = humanize_timedelta(timedelta=time_left)
                else:
                    time_str = ""
                msg += f"{user_str} "
                if time_str:
                    msg += _("__Remaining__: {time_left}\n").format(time_left=time_str)
                else:
                    msg += "\n"
        if channel_mutes:
            for channel_id, muted_users in channel_mutes.items():
                msg += _("__<#{channel_id}> Mutes__\n").format(channel_id=channel_id)
                for user_id, muted_user in muted_users.items():
                    user = ctx.guild.get_member(user_id)
                    user_str = f"<@!{user_id}>"

                    if muted_user.until:
                        time_left = muted_user.until - datetime.now(timezone.utc).timestamp()
                        time_str = humanize_timedelta(seconds=time_left)
                    else:
                        time_str = ""
                    msg += f"{user_str} "
                    if time_str:
                        msg += _("__Remaining__: {time_left}\n").format(time_left=time_str)
                    else:
                        msg += "\n"
        if msg:
            for page in pagify(msg):
                await ctx.maybe_send_embed(page)
            return

    @commands.command(usage="<users...> [time_and_reason]")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def mute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Mute users.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will use the set default time or indefinite if not set.

        Examples:
        `[p]mute @member1 @member2 spam 5 hours`
        `[p]mute @member1 3 days`

        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot mute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot mute yourself."))

        if not await mutes.check_for_mute_role(self.bot, ctx):
            return
        async with ctx.typing():
            duration = time_and_reason.get("duration", None)
            reason = time_and_reason.get("reason", None)
            log.debug(duration)
            time = ""
            until = None
            if duration:
                until = datetime.now(timezone.utc) + duration
                time = _(" for {duration}").format(duration=humanize_timedelta(timedelta=duration))
            author = ctx.message.author
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason, shorten=True)
            success_list = []
            issue_list = []
            for user in users:
                try:
                    muted_user = await mutes.mute_user(
                        self.bot,
                        guild=guild,
                        member=user,
                        author=author,
                        until=until,
                        reason=audit_reason,
                    )
                except MuteError as e:
                    issue_list.append(e)
                    continue

                if muted_user.issues:
                    # This will only have something if we did channel mutes
                    for issue in muted_user.issues:
                        if isinstance(issue, MuteError):
                            issue_list.append(issue)
                        elif user not in success_list:
                            success_list.append(user)
                else:
                    success_list.append(user)
                    log.debug(muted_user)
                    if muted_user.until:
                        delta = datetime.fromtimestamp(muted_user.until) - datetime.now()
                        time = _(" for {duration}").format(
                            duration=humanize_timedelta(timedelta=delta)
                        )

                # incase we only muted a user in 1 channel not all
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at.replace(tzinfo=timezone.utc),
                    "smute",
                    user,
                    author,
                    reason,
                    until=until,
                    channel=None,
                )
                await mutes.send_mute_dm_notification(
                    self.bot,
                    member=user,
                    moderator=author,
                    guild=guild,
                    mute_type=_("Server mute"),
                    reason=reason,
                    duration=duration,
                )
        if success_list:
            msg = _("{users} has been muted in this server{time}.")
            if len(success_list) > 1:
                msg = _("{users} have been muted in this server{time}.")
            await ctx.send(
                msg.format(users=humanize_list([f"{u}" for u in success_list]), time=time)
            )
        if issue_list:
            await self.handle_issues(ctx, issue_list)

    def parse_issues(self, issue: MuteError) -> str:
        # if isinstance(issue, MuteRoleMissingError):
        log.debug(issue.reason)
        reason_msg = _(MUTE_UNMUTE_ISSUES.get(issue.reason)) + "\n"
        channel_msg = ""
        error_msg = _("{member} could not be (un)muted for the following reasons:\n").format(
            member=str(issue.member)
        )
        error_msg += reason_msg or channel_msg
        return error_msg

    async def handle_issues(
        self,
        ctx: commands.Context,
        issue_list: List[MuteError],
    ) -> None:
        """
        This is to handle the various issues that can return for each user/channel
        """
        message = _(
            "Some users could not be properly muted. Would you like to see who, where, and why?"
        )

        can_react = ctx.channel.permissions_for(ctx.me).add_reactions
        if not can_react:
            message += " (y/n)"
        query: discord.Message = await ctx.send(message)
        if can_react:
            # noinspection PyAsyncCall
            start_adding_reactions(query, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(query, ctx.author)
            event = "reaction_add"
        else:
            pred = MessagePredicate.yes_or_no(ctx)
            event = "message"
        try:
            await ctx.bot.wait_for(event, check=pred, timeout=30)
        except asyncio.TimeoutError:
            await query.delete()
            return

        if not pred.result:
            if can_react:
                await query.delete()
            else:
                await ctx.send(_("OK then."))
            return
        else:
            if can_react:
                with contextlib.suppress(discord.Forbidden):
                    await query.clear_reactions()
            issue = "\n".join(self.parse_issues(issue) for issue in issue_list)
            resp = pagify(issue, page_length=1000)
            await ctx.send_interactive(resp)

    @commands.command(
        name="mutechannel", aliases=["channelmute"], usage="<users...> [time_and_reason]"
    )
    @checks.mod_or_permissions(manage_roles=True)
    @commands.bot_has_guild_permissions(manage_permissions=True)
    async def channel_mute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Mute a user in the current text channel.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will use the set default time or indefinite if not set.

        Examples:
        `[p]mutechannel @member1 @member2 spam 5 hours`
        `[p]mutechannel @member1 3 days`
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot mute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot mute yourself."))
        async with ctx.typing():
            duration = time_and_reason.get("duration", None)
            reason = time_and_reason.get("reason", None)
            time = ""
            until = None
            if duration:
                until = datetime.now(timezone.utc) + duration
                time = _(" for {duration}").format(duration=humanize_timedelta(timedelta=duration))
            author = ctx.message.author
            channel = ctx.message.channel
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason, shorten=True)
            issue_list = []
            success_list = []
            for user in users:
                try:
                    muted_user = await mutes.channel_mute_user(
                        self.bot,
                        guild=guild,
                        channel=channel,
                        author=author,
                        member=user,
                        until=until,
                        reason=audit_reason,
                    )
                except MuteError as e:
                    issue_list.append(e)
                    continue
                success_list.append(user)
                log.debug(muted_user)
                if muted_user.until:
                    delta = datetime.fromtimestamp(muted_user.until) - datetime.now()
                    time = _(" for {duration}").format(
                        duration=humanize_timedelta(timedelta=delta)
                    )

                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at.replace(tzinfo=timezone.utc),
                    "cmute",
                    user,
                    author,
                    reason,
                    until=until,
                    channel=channel,
                )
                await mutes.send_mute_dm_notification(
                    self.bot,
                    member=user,
                    moderator=author,
                    guild=guild,
                    mute_type=_("Channel mute"),
                    reason=reason,
                    duration=duration,
                )

        if success_list:
            msg = _("{users} has been muted in this channel{time}.")
            if len(success_list) > 1:
                msg = _("{users} have been muted in this channel{time}.")
            await channel.send(
                msg.format(users=humanize_list([f"{u}" for u in success_list]), time=time)
            )
        if issue_list:
            msg = _("The following users could not be muted\n")
            for user, issue in issue_list:
                msg += f"{user}: {issue}\n"
            await ctx.send_interactive(pagify(msg))

    @commands.command(usage="<users...> [reason]")
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def unmute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        reason: Optional[str] = None,
    ):
        """Unmute users.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        if not await mutes.check_for_mute_role(self.bot, ctx):
            return
        async with ctx.typing():
            guild = ctx.guild
            author = ctx.author
            audit_reason = get_audit_reason(author, reason, shorten=True)
            issue_list = []
            success_list = []

            for user in users:
                try:
                    muted_user = await mutes.unmute_user(
                        self.bot, guild=guild, author=author, member=user, reason=audit_reason
                    )
                except MuteError as e:
                    issue_list.append(e)
                    continue
                if muted_user.issues:
                    # This will only have something if we did channel mutes
                    for issue in muted_user.issues:
                        if isinstance(issue, MuteError):
                            issue_list.append(issue)
                        elif user not in success_list:
                            success_list.append(user)
                else:
                    success_list.append(user)
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at.replace(tzinfo=timezone.utc),
                    "sunmute",
                    user,
                    author,
                    reason,
                    until=None,
                )
                await mutes.send_mute_dm_notification(
                    self.bot,
                    member=user,
                    moderator=author,
                    guild=guild,
                    mute_type=_("Server unmute"),
                    reason=reason,
                )

        if success_list:
            await ctx.send(
                _("{users} unmuted in this server.").format(
                    users=humanize_list([f"{u}" for u in success_list])
                )
            )
        if issue_list:
            await self.handle_issues(ctx, issue_list)

    @checks.mod_or_permissions(manage_roles=True)
    @commands.command(name="unmutechannel", aliases=["channelunmute"], usage="<users...> [reason]")
    @commands.bot_has_guild_permissions(manage_permissions=True)
    async def unmute_channel(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        reason: Optional[str] = None,
    ):
        """Unmute a user in this channel.

        `<users...>` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        async with ctx.typing():
            channel = ctx.channel
            author = ctx.author
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason, shorten=True)
            success_list = []
            issue_list = []
            for user in users:
                try:
                    await mutes.channel_unmute_user(
                        self.bot,
                        guild=guild,
                        channel=channel,
                        author=author,
                        member=user,
                        reason=audit_reason,
                    )
                except MuteError as e:
                    issue_list.append(e)

                success_list.append(user)
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at.replace(tzinfo=timezone.utc),
                    "cunmute",
                    user,
                    author,
                    reason,
                    until=None,
                    channel=channel,
                )
                await mutes.send_mute_dm_notification(
                    member=user,
                    moderator=author,
                    guild=guild,
                    mute_type=_("Channel unmute"),
                    reason=reason,
                )
        if success_list:
            if channel.id in self._channel_mutes and self._channel_mutes[channel.id]:
                await self.config.channel(channel).muted_users.set(self._channel_mutes[channel.id])
            else:
                await self.config.channel(channel).muted_users.clear()
            await ctx.send(
                _("{users} unmuted in this channel.").format(
                    users=humanize_list([f"{u}" for u in success_list])
                )
            )
        if issue_list:
            msg = _("The following users could not be unmuted\n")
            for user, issue in issue_list:
                msg += f"{user}: {issue}\n"
            await ctx.send_interactive(pagify(msg))
