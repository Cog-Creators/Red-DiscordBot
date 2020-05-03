import asyncio
import contextlib
import discord
import logging

from abc import ABC
from typing import cast, Optional, Dict, List, Tuple
from datetime import datetime, timedelta

from .converters import MuteTime
from .voicemutes import VoiceMutes

from redbot.core.bot import Red
from redbot.core import commands, checks, i18n, modlog, Config
from redbot.core.utils.chat_formatting import humanize_timedelta, humanize_list
from redbot.core.utils.mod import get_audit_reason, is_allowed_by_hierarchy
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

T_ = i18n.Translator("Mutes", __file__)

_ = lambda s: s
mute_unmute_issues = {
    "already_muted": _("That user is already muted in this channel."),
    "already_unmuted": _("That user is not muted in this channel."),
    "hierarchy_problem": _(
        "I cannot let you do that. You are not higher than the user in the role hierarchy."
    ),
    "is_admin": _("That user cannot be muted, as they have the Administrator permission."),
    "permissions_issue": _(
        "Failed to mute user. I need the manage roles "
        "permission and the user I'm muting must be "
        "lower than myself in the role hierarchy."
    ),
    "left_guild": _("The user has left the server while applying an overwrite."),
    "unknown_channel": _("The channel I tried to mute the user in isn't found."),
    "role_missing": _("The mute role no longer exists."),
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


class Mutes(VoiceMutes, commands.Cog, metaclass=CompositeMetaClass):
    """
    Stuff for mutes goes here
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, 49615220001, force_registration=True)
        default_guild = {
            "mute_role": None,
            "respect_hierarchy": True,
            "muted_users": {},
            "default_time": {},
            "removed_users": [],
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(perms_cache={})
        self.config.register_channel(muted_users={})
        self._server_mutes: Dict[int, Dict[int, dict]] = {}
        self._channel_mutes: Dict[int, Dict[int, dict]] = {}
        self._ready = asyncio.Event()
        self.bot.loop.create_task(self.initialize())
        self._unmute_tasks = {}
        self._unmute_task = asyncio.create_task(self._handle_automatic_unmute())
        # dict of guild id, member id and time to be unmuted

    async def initialize(self):
        guild_data = await self.config.all_guilds()
        for g_id, mutes in guild_data.items():
            self._server_mutes[g_id] = mutes["muted_users"]
        channel_data = await self.config.all_channels()
        for c_id, mutes in channel_data.items():
            self._channel_mutes[c_id] = mutes["muted_users"]
        self._ready.set()

    async def cog_before_invoke(self, ctx: commands.Context):
        await self._ready.wait()

    def cog_unload(self):
        self._unmute_task.cancel()
        for task in self._unmute_tasks.values():
            task.cancel()

    async def _handle_automatic_unmute(self):
        await self.bot.wait_until_red_ready()
        await self._ready.wait()
        while True:
            # await self._clean_tasks()
            try:
                await self._handle_server_unmutes()
            except Exception:
                log.error("error checking server unmutes", exc_info=True)
            await asyncio.sleep(0.1)
            try:
                await self._handle_channel_unmutes()
            except Exception:
                log.error("error checking channel unmutes", exc_info=True)
            await asyncio.sleep(120)

    async def _clean_tasks(self):
        log.debug("Cleaning unmute tasks")
        is_debug = log.getEffectiveLevel() <= logging.DEBUG
        for task_id in list(self._unmute_tasks.keys()):
            task = self._unmute_tasks[task_id]

            if task.canceled():
                self._unmute_tasks.pop(task_id, None)
                continue

            if task.done():
                try:
                    r = task.result()
                except Exception:
                    if is_debug:
                        log.exception("Dead task when trying to unmute")
                self._unmute_tasks.pop(task_id, None)

    async def _handle_server_unmutes(self):
        log.debug("Checking server unmutes")
        for g_id, mutes in self._server_mutes.items():
            to_remove = []
            guild = self.bot.get_guild(g_id)
            if guild is None:
                continue
            for u_id, data in mutes.items():
                time_to_unmute = data["until"] - datetime.utcnow().timestamp()
                if time_to_unmute < 120.0:
                    self._unmute_tasks[f"{g_id}{u_id}"] = asyncio.create_task(
                        self._auto_unmute_user(guild, data)
                    )
                    to_remove.append(u_id)
            for u_id in to_remove:
                del self._server_mutes[g_id][u_id]
            await self.config.guild(guild).muted_users.set(self._server_mutes[g_id])

    async def _auto_unmute_user(self, guild: discord.Guild, data: dict):
        delay = 120 - (data["until"] - datetime.utcnow().timestamp())
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)
        try:
            member = guild.get_member(data["member"])
            author = guild.get_member(data["author"])
            if not member or not author:
                return
            success, message = await self.unmute_user(guild, author, member, _("Automatic unmute"))
            if success:
                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        datetime.utcnow(),
                        "sunmute",
                        member,
                        author,
                        _("Automatic unmute"),
                        until=None,
                    )
                except RuntimeError as e:
                    log.error(_("Error creating modlog case"), exc_info=e)
        except discord.errors.Forbidden:
            return

    async def _handle_channel_unmutes(self):
        log.debug("Checking channel unmutes")
        for c_id, mutes in self._channel_mutes.items():
            to_remove = []
            channel = self.bot.get_channel(c_id)
            if channel is None:
                continue
            for u_id, data in mutes.items():
                time_to_unmute = data["until"] - datetime.utcnow().timestamp()
                if time_to_unmute < 120.0:
                    self._unmute_tasks[f"{c_id}{u_id}"] = asyncio.create_task(
                        self._auto_channel_unmute_user(channel, data)
                    )
            for u_id in to_remove:
                del self._channel_mutes[c_id][u_id]
            await self.config.channel(channel).muted_users.set(self._channel_mutes[c_id])

    async def _auto_channel_unmute_user(self, channel: discord.TextChannel, data: dict):
        delay = 120 - (data["until"] - datetime.utcnow().timestamp())
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)
        try:
            member = channel.guild.get_member(data["member"])
            author = channel.guild.get_member(data["author"])
            if not member or not author:
                return
            success, message = await self.channel_unmute_user(
                channel.guild, channel, author, member, _("Automatic unmute")
            )
            if success:
                try:
                    await modlog.create_case(
                        self.bot,
                        channel.guild,
                        datetime.utcnow(),
                        "cunmute",
                        member,
                        author,
                        _("Automatic unmute"),
                        until=None,
                    )
                except RuntimeError as e:
                    log.error(_("Error creating modlog case"), exc_info=e)
        except discord.errors.Forbidden:
            return

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        if guild.id in self._server_mutes:
            if member.id in self._server_mutes[guild.id]:
                del self._server_mutes[guild.id][member.id]
        for channel in guild.channels:
            if channel.id in self._channel_mutes:
                if member.id in self._channel_mutes[channel.id]:
                    del self._channel_mutes[channel.id][member.id]
        mute_role = await self.config.guild(guild).mute_role()
        if not mute_role:
            return
        if mute_role in [r.id for r in member.roles]:
            async with self.config.guild(guild).removed_users() as removed_users:
                removed_users.append(member.id)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        mute_role = await self.config.guild(guild).mute_role()
        if not mute_role:
            return
        async with self.config.guild(guild).removed_users() as removed_users:
            if member.id in removed_users:
                removed_users.remove(member.id)
                role = guild.get_role(mute_role)
                if not role:
                    return
                try:
                    await member.add_roles(role, reason=_("Previously muted in this server."))
                except discord.errors.Forbidden:
                    return

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def muteset(self, ctx: commands.Context):
        """Mute settings."""
        pass

    @muteset.command(name="role")
    @checks.bot_has_permissions(manage_roles=True)
    async def mute_role(self, ctx: commands.Context, *, role: discord.Role = None):
        """Sets the role to be applied when muting a user.

            If no role is setup the bot will attempt to mute a user by setting
            channel overwrites in all channels to prevent the user from sending messages.
        """
        if not role:
            await self.config.guild(ctx.guild).mute_role.set(None)
            await ctx.send(_("Channel overwrites will be used for mutes instead."))
        else:
            await self.config.guild(ctx.guild).mute_role.set(role.id)
            await ctx.send(_("Mute role set to {role}").format(role=role.name))

    @muteset.command(name="makerole")
    @checks.bot_has_permissions(manage_roles=True)
    async def make_mute_role(self, ctx: commands.Context, *, name: str):
        """Create a Muted role.

            This will create a role and apply overwrites to all available channels
            to more easily setup muting a user.

            If you already have a muted role created on the server use
            `[p]muteset role ROLE_NAME_HERE`
        """
        perms = discord.Permissions()
        perms.update(send_messages=False, speak=False, add_reactions=False)
        try:
            role = await ctx.guild.create_role(
                name=name, permissions=perms, reason=_("Mute role setup")
            )
        except discord.errors.Forbidden:
            return
        for channel in ctx.guild.channels:
            overs = discord.PermissionOverwrite()
            if isinstance(channel, discord.TextChannel):
                overs.send_messages = False
                overs.add_reactions = False
            if isinstance(channel, discord.VoiceChannel):
                overs.speak = False
            try:
                await channel.set_permissions(role, overwrite=overs, reason=_("Mute role setup"))
            except discord.errors.Forbidden:
                continue
        await self.config.guild(ctx.guild).mute_role.set(role.id)
        await ctx.send(_("Mute role set to {role}").format(role=role.name))

    @muteset.command(name="time")
    async def default_mute_time(self, ctx: commands.Context, *, time: MuteTime):
        """
            Set the default mute time for the mute command.
        """
        data = time.get("duration", {})
        if not data:
            await self.config.guild(ctx.guild).default_time.set(data)
            await ctx.send(_("Default mute time removed."))
        else:
            await self.config.guild(ctx.guild).default_time.set(data)
            await ctx.send(
                _("Default mute time set to {time}").format(
                    time=humanize_timedelta(timedelta=timedelta(**data))
                )
            )

    @commands.command()
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

        `[users]...` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason={}]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will be indefinite.

        Examples:
        `[p]mute @member1 @member2 spam 5 hours`
        `[p]mute @member1 3 days`

        """
        if not users:
            return await ctx.send_help()
        duration = time_and_reason.get("duration", {})
        reason = time_and_reason.get("reason", None)
        time = ""
        until = None
        if duration:
            until = datetime.utcnow() + timedelta(**duration)
            time = _(" for ") + humanize_timedelta(timedelta=timedelta(**duration))
        else:
            default_duration = await self.config.guild(ctx.guild).default_time()
            if default_duration:
                until = datetime.utcnow() + timedelta(**default_duration)
                time = _(" for ") + humanize_timedelta(timedelta=timedelta(**default_duration))
        author = ctx.message.author
        guild = ctx.guild
        audit_reason = get_audit_reason(author, reason)
        success_list = []
        for user in users:
            success, issue = await self.mute_user(guild, author, user, audit_reason)
            if success:
                success_list.append(user)
                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "smute",
                        user,
                        author,
                        reason,
                        until=until,
                        channel=None,
                    )
                except RuntimeError as e:
                    log.error(_("Error creating modlog case"), exc_info=e)
        if not success_list:
            return await ctx.send(issue)
        if until:
            if ctx.guild.id not in self._server_mutes:
                self._server_mutes[ctx.guild.id] = {}
            for user in success_list:
                mute = {
                    "author": ctx.message.author.id,
                    "member": user.id,
                    "until": until.timestamp(),
                }
                self._server_mutes[ctx.guild.id][user.id] = mute
            await self.config.guild(ctx.guild).muted_users.set(self._server_mutes[ctx.guild.id])
        verb = _("has")
        if len(success_list) > 1:
            verb = _("have")
        await ctx.send(
            _("{users} {verb} been muted in this server{time}.").format(
                users=humanize_list([f"{u}" for u in success_list]), verb=verb, time=time
            )
        )
        if issue:
            message = _(
                    "{users} could not be muted in some channels. "
                    "Would you like to see which channels and why?"
                ).format(users=humanize_list([f"{u}" for u in users]))
            await self.handle_issues(ctx, message)

    async def handle_issues(self, ctx: commands.Context, message: str) -> None:
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
            await ctx.send(issue)

    @commands.command(name="mutechannel", aliases=["channelmute"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def channel_mute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Mute a user in the current text channel.

        `[users]...` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason={}]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will be indefinite.

        Examples:
        `[p]mutechannel @member1 @member2 spam 5 hours`
        `[p]mutechannel @member1 3 days`
        """
        if not users:
            return await ctx.send_help()
        duration = time_and_reason.get("duration", {})
        reason = time_and_reason.get("reason", None)
        until = None
        time = ""
        if duration:
            until = datetime.utcnow() + timedelta(**duration)
            time = _(" for ") + humanize_timedelta(timedelta=timedelta(**duration))
        else:
            default_duration = await self.config.guild(ctx.guild).default_time()
            if default_duration:
                until = datetime.utcnow() + timedelta(**default_duration)
                time = _(" for ") + humanize_timedelta(timedelta=timedelta(**default_duration))
        author = ctx.message.author
        channel = ctx.message.channel
        guild = ctx.guild
        audit_reason = get_audit_reason(author, reason)
        success_list = []
        for user in users:
            success, issue = await self.channel_mute_user(
                guild, channel, author, user, audit_reason
            )
            if success:
                success_list.append(user)

                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        ctx.message.created_at,
                        "cmute",
                        user,
                        author,
                        reason,
                        until=until,
                        channel=channel,
                    )
                except RuntimeError as e:
                    log.error(_("Error creating modlog case"), exc_info=e)
        if success_list:
            if until:
                if channel.id not in self._channel_mutes:
                    self._channel_mutes[channel.id] = {}
                for user in success_list:
                    mute = {
                        "author": ctx.message.author.id,
                        "member": user.id,
                        "until": until.timestamp(),
                    }
                    self._channel_mutes[channel.id][user.id] = mute
                await self.config.channel(channel).muted_users.set(self._channel_mutes[channel.id])
            verb = _("has")
            if len(success_list) > 1:
                verb = _("have")
            await channel.send(
                _("{users} {verb} been muted in this channel{time}.").format(
                    users=humanize_list([f"{u}" for u in success_list]), verb=verb, time=time
                )
            )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.mod_or_permissions(manage_roles=True)
    async def unmute(
        self, ctx: commands.Context, users: commands.Greedy[discord.Member], *, reason: str = None
    ):
        """Unmute users.

        `[users]...` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        guild = ctx.guild
        author = ctx.author
        audit_reason = get_audit_reason(author, reason)
        success_list = []
        for user in users:
            success, issue = await self.unmute_user(guild, author, user, audit_reason)
            if success:
                success_list.append(user)
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
                    log.error(_("Error creating modlog case"), exc_info=e)
        if not success_list:
            return await ctx.send(issue)
        if ctx.guild.id in self._server_mutes:
            if user.id in self._server_mutes[ctx.guild.id]:
                for user in success_list:
                    del self._server_mutes[ctx.guild.id][user.id]
                await self.config.guild(ctx.guild).muted_users.set(
                    self._server_mutes[ctx.guild.id]
                )
        await ctx.send(
            _("{users} unmuted in this server.").format(
                users=humanize_list([f"{u}" for u in success_list])
            )
        )
        if issue:
            message = _(
                    "{users} could not be unmuted in some channels. "
                    "Would you like to see which channels and why?"
                ).format(users=humanize_list([f"{u}" for u in users]))
            await self.handle_issues(ctx, message)

    @checks.mod_or_permissions(manage_roles=True)
    @commands.command(name="channelunmute", aliases=["unmutechannel"])
    @commands.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    async def unmute_channel(
        self, ctx: commands.Context, users: commands.Greedy[discord.Member], *, reason: str = None
    ):
        """Unmute a user in this channel.

        `[users]...` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        audit_reason = get_audit_reason(author, reason)
        success_list = []
        for user in users:
            success, message = await self.channel_unmute_user(
                guild, channel, author, user, audit_reason
            )

            if success:
                success_list.append(user)
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
                    log.error(_("Error creating modlog case"), exc_info=e)
        if success_list:
            for user in success_list:
                if (
                    channel.id in self._channel_mutes
                    and user.id in self._channel_mutes[channel.id]
                ):
                    del self._channel_mutes[channel.id][user.id]
                    await self.config.channel(channel).muted_users.set(
                        self._channel_mutes[channel.id]
                    )
            await ctx.send(
                _("{users} unmuted in this channel.").format(
                    users=humanize_list([f"{u}" for u in success_list])
                )
            )

    async def mute_user(
        self, guild: discord.Guild, author: discord.Member, user: discord.Member, reason: str,
    ) -> Tuple[bool, Optional[str]]:
        """
            Handles muting users
        """
        mute_role = await self.config.guild(guild).mute_role()
        if mute_role:
            try:
                if not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
                    return False, _(mute_unmute_issues["hierarchy_problem"])
                role = guild.get_role(mute_role)
                if not role:
                    return False, mute_unmute_issues["role_missing"]
                await user.add_roles(role, reason=reason)
            except discord.errors.Forbidden:
                return False, mute_unmute_issues["permissions_issue"]
            return True, None
        else:
            mute_success = []
            for channel in guild.channels:
                success, issue = await self.channel_mute_user(guild, channel, author, user, reason)
                if not success:
                    mute_success.append(f"{channel.mention} - {issue}")
                await asyncio.sleep(0.1)
            if mute_success and len(mute_success) == len(guild.channels):
                return False, "\n".join(s for s in mute_success)
            elif mute_success and len(mute_success) != len(guild.channels):
                return True, "\n".join(s for s in mute_success)
            else:
                return True, None

    async def unmute_user(
        self, guild: discord.Guild, author: discord.Member, user: discord.Member, reason: str,
    ) -> Tuple[bool, Optional[str]]:
        """
            Handles muting users
        """
        mute_role = await self.config.guild(guild).mute_role()
        if mute_role:
            try:
                if not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
                    return False, _(mute_unmute_issues["hierarchy_problem"])
                role = guild.get_role(mute_role)
                if not role:
                    return False, mute_unmute_issues["role_missing"]
                await user.remove_roles(role, reason=reason)
            except discord.errors.Forbidden:
                return False, mute_unmute_issues["permissions_issue"]
            return True, None
        else:
            mute_success = []
            for channel in guild.channels:
                success, issue = await self.channel_unmute_user(
                    guild, channel, author, user, reason
                )
                if not success:
                    mute_success.append(f"{channel.mention} - {issue}")
                await asyncio.sleep(0.1)
            if mute_success:
                return False, "\n".join(s for s in mute_success)
            else:
                return True, None

    async def channel_mute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        reason: str,
    ) -> Tuple[bool, Optional[str]]:
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)

        if permissions.administrator:
            return False, _(mute_unmute_issues["is_admin"])

        new_overs = {}
        if not isinstance(channel, discord.TextChannel):
            new_overs.update(speak=False)
        if not isinstance(channel, discord.VoiceChannel):
            new_overs.update(send_messages=False, add_reactions=False)

        if not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
            return False, _(mute_unmute_issues["hierarchy_problem"])

        old_overs = {k: getattr(overwrites, k) for k in new_overs}
        overwrites.update(**new_overs)
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, _(mute_unmute_issues["permissions_issue"])
        except discord.NotFound as e:
            if e.code == 10003:
                return False, _(mute_unmute_issues["unknown_channel"])
            elif e.code == 10009:
                return False, _(mute_unmute_issues["left_guild"])
        else:
            await self.config.member(user).set_raw("perms_cache", str(channel.id), value=old_overs)
        return True, None

    async def channel_unmute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        reason: str,
    ) -> Tuple[bool, Optional[str]]:
        overwrites = channel.overwrites_for(user)
        perms_cache = await self.config.member(user).perms_cache()

        if channel.id in perms_cache:
            old_values = perms_cache[channel.id]
        else:
            old_values = {"send_messages": None, "add_reactions": None, "speak": None}

        if not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
            return False, _(mute_unmute_issues["hierarchy_problem"])

        overwrites.update(**old_values)
        try:
            if overwrites.is_empty():
                await channel.set_permissions(
                    user, overwrite=cast(discord.PermissionOverwrite, None), reason=reason
                )
            else:
                await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            return False, _(mute_unmute_issues["permissions_issue"])
        except discord.NotFound as e:
            if e.code == 10003:
                return False, _(mute_unmute_issues["unknown_channel"])
            elif e.code == 10009:
                return False, _(mute_unmute_issues["left_guild"])
        else:
            await self.config.member(user).clear_raw("perms_cache", str(channel.id))
        return True, None
