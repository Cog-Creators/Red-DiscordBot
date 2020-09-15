import asyncio
import contextlib
import discord
import logging

from abc import ABC
from copy import copy
from typing import cast, Optional, Dict, List, Tuple, Literal, Coroutine, Union
from datetime import datetime, timedelta, timezone

from .converters import MuteTime
from .voicemutes import VoiceMutes

from redbot.core.bot import Red
from redbot.core import commands, checks, i18n, modlog, Config
from redbot.core.utils.chat_formatting import humanize_timedelta, humanize_list, pagify
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
        "Failed to mute or unmute user. I need the manage roles "
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
            "sent_instructions": False,
            "mute_role": None,
            "respect_hierarchy": True,
            "muted_users": {},
            "default_time": {},
            "removed_users": {},
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(perms_cache={})
        self.config.register_channel(muted_users={})
        self._server_mutes: Dict[int, Dict[int, dict]] = {}
        self._channel_mutes: Dict[int, Dict[int, dict]] = {}
        self._ready = asyncio.Event()
        self.bot.loop.create_task(self.initialize())
        self._unmute_tasks: Dict[str, Coroutine] = {}
        self._unmute_task = asyncio.create_task(self._handle_automatic_unmute())
        # dict of guild id, member id and time to be unmuted

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester != "discord_deleted_user":
            return

        await self._ready.wait()
        all_members = await self.config.all_members()
        for g_id, m_id in all_members.items():
            if m_id == user_id:
                await self.config.member_from_ids(g_id, m_id).clear()

    async def initialize(self):
        guild_data = await self.config.all_guilds()
        for g_id, mutes in guild_data.items():
            self._server_mutes[g_id] = {}
            for user_id, mute in mutes["muted_users"].items():
                self._server_mutes[g_id][int(user_id)] = mute
        channel_data = await self.config.all_channels()
        for c_id, mutes in channel_data.items():
            self._channel_mutes[c_id] = {}
            for user_id, mute in mutes["muted_users"].items():
                self._channel_mutes[c_id][int(user_id)] = mute
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
            await self._clean_tasks()
            try:
                await self._handle_server_unmutes()
            except Exception:
                log.error("error checking server unmutes", exc_info=True)
            await asyncio.sleep(0.1)
            try:
                await self._handle_channel_unmutes()
            except Exception:
                log.error("error checking channel unmutes", exc_info=True)
            await asyncio.sleep(30)

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
        to_clear = []
        for g_id, mutes in self._server_mutes.items():
            to_remove = []
            guild = self.bot.get_guild(g_id)
            if guild is None:
                continue
            for u_id, data in mutes.items():
                if data["until"] is None:
                    continue
                time_to_unmute = data["until"] - datetime.now(timezone.utc).timestamp()
                if time_to_unmute < 60:
                    self._unmute_tasks[f"{g_id}{u_id}"] = asyncio.create_task(
                        self._auto_unmute_user(guild, data)
                    )
                    to_remove.append(u_id)
            for u_id in to_remove:
                del self._server_mutes[g_id][u_id]
            if self._server_mutes[g_id] == {}:
                to_clear.append(g_id)
            await self.config.guild(guild).muted_users.set(self._server_mutes[g_id])
        for g_id in to_clear:
            await self.config.guild_from_id(g_id).muted_users.clear()

    async def _auto_unmute_user(self, guild: discord.Guild, data: dict):
        delay = data["until"] - datetime.now(timezone.utc).timestamp()
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)
        try:
            member = guild.get_member(data["member"])
            author = guild.get_member(data["author"])
            if not member:
                return
            success, message = await self.unmute_user(guild, author, member, _("Automatic unmute"))
            if success:
                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        datetime.now(timezone.utc),
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
        to_clear = []
        for c_id, mutes in self._channel_mutes.items():
            to_remove = []
            channel = self.bot.get_channel(c_id)
            if channel is None:
                continue
            for u_id, data in mutes.items():
                if not data or not data["until"]:
                    continue
                time_to_unmute = data["until"] - datetime.now(timezone.utc).timestamp()
                if time_to_unmute < 120.0:
                    self._unmute_tasks[f"{c_id}{u_id}"] = asyncio.create_task(
                        self._auto_channel_unmute_user(channel, data)
                    )
            for u_id in to_remove:
                del self._channel_mutes[c_id][u_id]
            if self._channel_mutes[c_id] == {}:
                to_clear.append(c_id)
            await self.config.channel(channel).muted_users.set(self._channel_mutes[c_id])
        for c_id in to_clear:
            await self.config.channel_from_id(c_id).muted_users.clear()

    async def _auto_channel_unmute_user(self, channel: discord.TextChannel, data: dict):
        delay = data["until"] - datetime.now(timezone.utc).timestamp()
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)
        try:
            member = channel.guild.get_member(data["member"])
            author = channel.guild.get_member(data["author"])
            if not member or not author:
                return
            success = await self.channel_unmute_user(
                channel.guild, channel, author, member, _("Automatic unmute")
            )
            if success["success"]:
                try:
                    await modlog.create_case(
                        self.bot,
                        channel.guild,
                        datetime.now(timezone.utc),
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
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Used to handle the cache if a member manually has the muted role removed
        """
        guild = before.guild
        mute_role_id = await self.config.guild(before.guild).mute_role()
        mute_role = guild.get_role(mute_role_id)
        if not mute_role:
            return
        b = set(before.roles)
        a = set(after.roles)
        roles_removed = list(b - a)
        roles_added = list(a - b)
        if mute_role in roles_removed:
            # send modlog case for unmute and remove from cache
            if guild.id not in self._server_mutes:
                # they weren't a tracked mute so we can return early
                return
            if after.id in self._server_mutes[guild.id]:
                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        datetime.utcnow(),
                        "sunmute",
                        after,
                        None,
                        _("Manually removed mute role"),
                    )
                except RuntimeError as e:
                    log.error(_("Error creating modlog case"), exc_info=e)
                del self._server_mutes[guild.id][after.id]
        if mute_role in roles_added:
            # send modlog case for mute and add to cache
            if guild.id not in self._server_mutes:
                # initialize the guild in the cache to prevent keyerrors
                self._server_mutes[guild.id] = {}
            if after.id not in self._server_mutes[guild.id]:
                try:
                    await modlog.create_case(
                        self.bot,
                        guild,
                        datetime.utcnow(),
                        "smute",
                        after,
                        None,
                        _("Manually applied mute role"),
                    )
                except RuntimeError as e:
                    log.error(_("Error creating modlog case"), exc_info=e)
                self._server_mutes[guild.id][after.id] = {
                    "author": None,
                    "member": after.id,
                    "until": None,
                }
        if guild.id in self._server_mutes:
            await self.config.guild(guild).muted_users.set(self._server_mutes[guild.id])

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        """
        This handles manually removing overwrites for a user that has been muted
        """
        if after.id in self._channel_mutes:
            before_perms: Dict[int, Dict[str, Optional[bool]]] = {
                o.id: {name: attr for name, attr in p} for o, p in before.overwrites.items()
            }
            after_perms: Dict[int, Dict[str, Optional[bool]]] = {
                o.id: {name: attr for name, attr in p} for o, p in after.overwrites.items()
            }
            to_del: List[int] = []
            for user_id in self._channel_mutes[after.id].keys():
                if user_id in before_perms and (
                    user_id not in after_perms or after_perms[user_id]["send_messages"]
                ):
                    user = after.guild.get_member(user_id)
                    if not user:
                        user = discord.Object(id=user_id)
                    log.debug(f"{user} - {type(user)}")
                    to_del.append(user_id)
                    try:
                        log.debug("creating case")
                        await modlog.create_case(
                            self.bot,
                            after.guild,
                            datetime.utcnow(),
                            "cunmute",
                            user,
                            None,
                            _("Manually removed channel overwrites"),
                            until=None,
                            channel=after,
                        )
                        log.debug("created case")
                    except RuntimeError as e:
                        log.error(_("Error creating modlog case"), exc_info=e)
            for u_id in to_del:
                del self._channel_mutes[after.id][u_id]
            await self.config.channel(after).muted_users.set(self._channel_mutes[after.id])

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        until = None
        if guild.id in self._server_mutes:
            if member.id in self._server_mutes[guild.id]:
                until = self._server_mutes[guild.id][member.id]["until"]
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
                removed_users[str(member.id)] = int(until) if until else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        mute_role = await self.config.guild(guild).mute_role()
        if not mute_role:
            return
        async with self.config.guild(guild).removed_users() as removed_users:
            if str(member.id) in removed_users:
                until_ts = removed_users[str(member.id)]
                until = datetime.fromtimestamp(until_ts, tz=timezone.utc) if until_ts else None
                # datetime is required to utilize the mutes method
                if until and until < datetime.now(tz=timezone.utc):
                    return
                removed_users.pop(str(member.id))
                role = guild.get_role(mute_role)
                if not role:
                    return
                await self.mute_user(
                    guild, guild.me, member, until, _("Previously muted in this server.")
                )

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
            await self.config.guild(ctx.guild).sent_instructions(False)
            # reset this to warn users next time they may have accidentally
            # removed the mute role
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
        async with ctx.typing():
            perms = discord.Permissions()
            perms.update(send_messages=False, speak=False, add_reactions=False)
            try:
                role = await ctx.guild.create_role(
                    name=name, permissions=perms, reason=_("Mute role setup")
                )
            except discord.errors.Forbidden:
                return await ctx.send(_("I could not create a muted role in this server."))
            errors = []
            tasks = []
            for channel in ctx.guild.channels:
                tasks.append(self._set_mute_role_overwrites(role, channel))
            errors = await asyncio.gather(*tasks)
            if any(errors):
                msg = _(
                    "I could not set overwrites for the following channels: {channels}"
                ).format(channels=humanize_list([i for i in errors if i]))
                for page in pagify(msg):
                    await ctx.send(page)
            await self.config.guild(ctx.guild).mute_role.set(role.id)
            await ctx.send(_("Mute role set to {role}").format(role=role.name))

    async def _set_mute_role_overwrites(
        self, role: discord.Role, channel: discord.abc.GuildChannel
    ) -> Optional[str]:
        """
        This sets the supplied role and channel overwrites to what we want
        by default for a mute role
        """
        overs = discord.PermissionOverwrite()
        if isinstance(channel, discord.TextChannel):
            overs.send_messages = False
            overs.add_reactions = False
        if isinstance(channel, discord.VoiceChannel):
            overs.speak = False
        try:
            await channel.set_permissions(role, overwrite=overs, reason=_("Mute role setup"))
            return
        except discord.errors.Forbidden:
            return channel.mention

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

    async def _check_for_mute_role(self, ctx: commands.Context) -> bool:
        """
        This explains to the user whether or not mutes are setup correctly for
        automatic unmutes.
        """
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        mute_role = ctx.guild.get_role(mute_role_id)
        sent_instructions = await self.config.guild(ctx.guild).sent_instructions()
        if mute_role or sent_instructions:
            return True
        else:
            msg = _(
                "This server does not have a mute role setup, "
                "are you sure you want to continue with channel "
                "overwrites? (Note: Overwrites will not be automatically unmuted."
                " You can setup a mute role with `{prefix}muteset role` or "
                "`{prefix}muteset makerole` if you just want a basic setup.)\n\n"
            ).format(prefix=ctx.clean_prefix)
            can_react = ctx.channel.permissions_for(ctx.me).add_reactions
            if can_react:
                msg += _(
                    "Reacting with \N{WHITE HEAVY CHECK MARK} will continue "
                    "the mute with overwrites and stop this message from appearing again, "
                    "Reacting with \N{NEGATIVE SQUARED CROSS MARK} will end the mute attempt."
                )
            else:
                msg += _(
                    "Saying `yes` will continue "
                    "the mute with overwrites and stop this message from appearing again, "
                    "saying `no` will end the mute attempt."
                )
            query: discord.Message = await ctx.send(msg)
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
                return False

            if not pred.result:
                if can_react:
                    await query.delete()
                else:
                    await ctx.send(_("OK then."))

                return False
            else:
                if can_react:
                    with contextlib.suppress(discord.Forbidden):
                        await query.clear_reactions()
                await self.config.guild(ctx.guild).sent_instructions.set(True)
                return True

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def activemutes(self, ctx: commands.Context):
        """
        Displays active mutes on this server.
        """

        msg = ""
        to_del = []
        if ctx.guild.id in self._server_mutes:
            mutes_data = self._server_mutes[ctx.guild.id]
            to_rem = []
            if mutes_data:

                msg += _("__Server Mutes__\n")
                for user_id, mutes in mutes_data.items():
                    if not mutes:
                        to_rem.append(user_id)
                        continue
                    user = ctx.guild.get_member(user_id)
                    if not user:
                        user_str = f"<@!{user_id}>"
                    else:
                        user_str = user.mention
                    if mutes["until"]:
                        time_left = timedelta(
                            seconds=mutes["until"] - datetime.now(timezone.utc).timestamp()
                        )
                        time_str = humanize_timedelta(timedelta=time_left)
                    else:
                        time_str = ""
                    msg += _("{member}").format(member=user_str)
                    if time_str:
                        msg += _("__Remaining__: {time_left}\n").format(time_left=time_str)
                    else:
                        msg += "\n"
            for _id in to_rem:
                try:
                    del self._server_mutes[ctx.guild.id][_id]
                except KeyError:
                    pass
        for channel_id, mutes_data in self._channel_mutes.items():
            if not mutes_data:
                to_del.append(channel_id)
                continue
            if channel_id in [c.id for c in ctx.guild.channels]:
                msg += _("__<#{channel_id}> Mutes__\n").format(channel_id=channel_id)
                for user_id, mutes in mutes_data.items():
                    if not mutes:
                        continue
                    user = ctx.guild.get_member(user_id)
                    if not user:
                        user_str = f"<@!{user_id}>"
                    else:
                        user_str = user.mention
                    if mutes["until"]:
                        time_left = timedelta(
                            seconds=mutes["until"] - datetime.now(timezone.utc).timestamp()
                        )
                        time_str = humanize_timedelta(timedelta=time_left)
                    else:
                        time_str = ""
                    msg += _("{member} ").format(member=user_str)
                    if time_str:
                        msg += _("__Remaining__: {time_left}\n").format(time_left=time_str)
                    else:
                        msg += "\n"
        for c in to_del:
            del self._channel_mutes[c]
        if msg:
            for page in pagify(msg):
                await ctx.maybe_send_embed(page)
            return
        await ctx.maybe_send_embed(_("There are no mutes on this server right now."))

    @commands.command(usage="[users...] [time_and_reason]")
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

        `[users...]` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will be indefinite.

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
        if not await self._check_for_mute_role(ctx):
            return
        async with ctx.typing():
            duration = time_and_reason.get("duration", {})
            reason = time_and_reason.get("reason", None)
            time = ""
            until = None
            if duration:
                until = datetime.now(timezone.utc) + timedelta(**duration)
                time = _(" for ") + humanize_timedelta(timedelta=timedelta(**duration))
            else:
                default_duration = await self.config.guild(ctx.guild).default_time()
                if default_duration:
                    until = datetime.now(timezone.utc) + timedelta(**default_duration)
                    time = _(" for ") + humanize_timedelta(timedelta=timedelta(**default_duration))
            author = ctx.message.author
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason)
            success_list = []
            for user in users:
                success, issue = await self.mute_user(guild, author, user, until, audit_reason)
                if success:
                    success_list.append(user)
                    try:
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
                    except RuntimeError as e:
                        log.error(_("Error creating modlog case"), exc_info=e)
            if not success_list and issue:
                message = _(
                    "{users} could not be muted in some channels. "
                    "Would you like to see which channels and why?"
                ).format(users=humanize_list([f"{u}" for u in users]))
                return await self.handle_issues(ctx, message, issue)
            if ctx.guild.id not in self._server_mutes:
                self._server_mutes[ctx.guild.id] = {}
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
                await self.handle_issues(ctx, message, issue)

    async def handle_issues(self, ctx: commands.Context, message: str, issue: str) -> None:
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
            resp = pagify(issue)
            await ctx.send_interactive(resp)

    @commands.command(
        name="mutechannel", aliases=["channelmute"], usage="[users...] [time_and_reason]"
    )
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def channel_mute(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        time_and_reason: MuteTime = {},
    ):
        """Mute a user in the current text channel.

        `[users...]` is a space separated list of usernames, ID's, or mentions.
        `[time_and_reason]` is the time to mute for and reason. Time is
        any valid time length such as `30 minutes` or `2 days`. If nothing
        is provided the mute will be indefinite.

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
        if not await self._check_for_mute_role(ctx):
            return
        async with ctx.typing():
            duration = time_and_reason.get("duration", {})
            reason = time_and_reason.get("reason", None)
            until = None
            time = ""
            if duration:
                until = datetime.now(timezone.utc) + timedelta(**duration)
                time = _(" for ") + humanize_timedelta(timedelta=timedelta(**duration))
            else:
                default_duration = await self.config.guild(ctx.guild).default_time()
                if default_duration:
                    until = datetime.now(timezone.utc) + timedelta(**default_duration)
                    time = _(" for ") + humanize_timedelta(timedelta=timedelta(**default_duration))
            author = ctx.message.author
            channel = ctx.message.channel
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason)
            success_list = []
            for user in users:
                success = await self.channel_mute_user(
                    guild, channel, author, user, until, audit_reason
                )
                if success["success"]:
                    success_list.append(user)

                    try:
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
                    except RuntimeError as e:
                        log.error(_("Error creating modlog case"), exc_info=e)
                else:
                    return await ctx.send(success["reason"])
            if success_list:
                verb = _("has")
                if len(success_list) > 1:
                    verb = _("have")
                await channel.send(
                    _("{users} {verb} been muted in this channel{time}.").format(
                        users=humanize_list([f"{u}" for u in success_list]), verb=verb, time=time
                    )
                )

    @commands.command(usage="[users...] [reason]")
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

        `[users...]` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        if not await self._check_for_mute_role(ctx):
            return
        async with ctx.typing():
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
                            ctx.message.created_at.replace(tzinfo=timezone.utc),
                            "sunmute",
                            user,
                            author,
                            reason,
                            until=None,
                        )
                    except RuntimeError as e:
                        log.error(_("Error creating modlog case"), exc_info=e)
            if not success_list and issue:
                message = _(
                    "{users} could not be muted in some channels. "
                    "Would you like to see which channels and why?"
                ).format(users=humanize_list([f"{u}" for u in users]))
                return await self.handle_issues(ctx, message, issue)

            if ctx.guild.id in self._server_mutes and self._server_mutes[ctx.guild.id]:
                await self.config.guild(ctx.guild).muted_users.set(
                    self._server_mutes[ctx.guild.id]
                )
            else:
                await self.config.guild(ctx.guild).muted_users.clear()
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
                await self.handle_issues(ctx, message, issue)

    @checks.mod_or_permissions(manage_roles=True)
    @commands.command(name="unmutechannel", aliases=["channelunmute"], usage="[users...] [reason]")
    @commands.guild_only()
    async def unmute_channel(
        self,
        ctx: commands.Context,
        users: commands.Greedy[discord.Member],
        *,
        reason: Optional[str] = None,
    ):
        """Unmute a user in this channel.

        `[users...]` is a space separated list of usernames, ID's, or mentions.
        `[reason]` is the reason for the unmute.
        """
        if not users:
            return await ctx.send_help()
        if ctx.me in users:
            return await ctx.send(_("You cannot unmute me."))
        if ctx.author in users:
            return await ctx.send(_("You cannot unmute yourself."))
        if not await self._check_for_mute_role(ctx):
            return
        async with ctx.typing():
            channel = ctx.channel
            author = ctx.author
            guild = ctx.guild
            audit_reason = get_audit_reason(author, reason)
            success_list = []
            for user in users:
                success = await self.channel_unmute_user(
                    guild, channel, author, user, audit_reason
                )

                if success["success"]:
                    success_list.append(user)
                    try:
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
                    except RuntimeError as e:
                        log.error(_("Error creating modlog case"), exc_info=e)
                else:
                    return await ctx.send(success["reason"])
            if success_list:
                if self._channel_mutes[channel.id]:
                    await self.config.channel(channel).set(self._channel_mutes[channel.id])
                else:
                    await self.config.channel(channel).muted_users.clear()
                await ctx.send(
                    _("{users} unmuted in this channel.").format(
                        users=humanize_list([f"{u}" for u in success_list])
                    )
                )

    async def mute_user(
        self,
        guild: discord.Guild,
        author: discord.Member,
        user: discord.Member,
        until: Optional[datetime] = None,
        reason: Optional[str] = None,
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

                # This is here to prevent the modlog case from happening on role updates
                # we need to update the cache early so it's there before we receive the member_update event
                if guild.id not in self._server_mutes:
                    self._server_mutes[guild.id] = {}

                self._server_mutes[guild.id][user.id] = {
                    "author": author.id,
                    "member": user.id,
                    "until": until.timestamp() if until else None,
                }
                await user.add_roles(role, reason=reason)
                await self.config.guild(guild).muted_users.set(self._server_mutes[guild.id])
            except discord.errors.Forbidden:
                del self._server_mutes[guild.id][
                    user.id
                ]  # this is here so we don't have a bad cache
                return False, mute_unmute_issues["permissions_issue"]
            return True, None
        else:
            mute_success = []
            perms_cache = {}
            tasks = []
            for channel in guild.channels:
                tasks.append(self.channel_mute_user(guild, channel, author, user, until, reason))
            task_result = await asyncio.gather(*tasks)
            for task in task_result:
                if not task["success"]:
                    chan = task["channel"].mention
                    issue = task["issue"]
                    mute_success.append(f"{chan} - {issue}")
                else:
                    chan_id = task["channel"].id
                    perms_cache[str(chan_id)] = issue.get("old_overs")
            await self.config.member(user).perms_cache.set(perms_cache)
            if mute_success and len(mute_success) == len(guild.channels):
                return False, "\n".join(s for s in mute_success)
            elif mute_success and len(mute_success) != len(guild.channels):
                return True, "\n".join(s for s in mute_success)
            else:
                return True, None

    async def unmute_user(
        self,
        guild: discord.Guild,
        author: discord.Member,
        user: discord.Member,
        reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Handles muting users
        """

        mute_role = await self.config.guild(guild).mute_role()
        _temp = None  # used to keep the cache incase of permissions errors
        if mute_role:
            try:
                if not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
                    return False, _(mute_unmute_issues["hierarchy_problem"])
                role = guild.get_role(mute_role)
                if not role:
                    return False, mute_unmute_issues["role_missing"]
                if guild.id in self._server_mutes:
                    if user.id in self._server_mutes[guild.id]:
                        _temp = copy(self._server_mutes[guild.id][user.id])
                        del self._server_mutes[guild.id][user.id]
                await user.remove_roles(role, reason=reason)
            except discord.errors.Forbidden:
                if _temp:
                    self._server_mutes[guild.id][user.id] = _temp
                return False, mute_unmute_issues["permissions_issue"]
            return True, None
        else:
            mute_success = []
            tasks = []
            for channel in guild.channels:
                tasks.append(self.channel_unmute_user(guild, channel, author, user, reason))
            results = await asyncio.gather(*tasks)
            for task in results:
                if not task["success"]:
                    chan = task["channel"].mention
                    issue = task["issue"]
                    mute_success.append(f"{chan} - {issue}")
            await self.config.member(user).clear()
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
        until: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Optional[Union[discord.abc.GuildChannel, str, bool]]]:
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)

        if permissions.administrator:
            return {
                "success": False,
                "channel": channel,
                "reason": _(mute_unmute_issues["is_admin"]),
            }

        new_overs: dict = {}
        if not isinstance(channel, discord.TextChannel):
            new_overs.update(speak=False)
        if not isinstance(channel, discord.VoiceChannel):
            new_overs.update(send_messages=False, add_reactions=False)

        if not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
            return {
                "success": False,
                "channel": channel,
                "reason": _(mute_unmute_issues["hierarchy_problem"]),
            }

        old_overs = {k: getattr(overwrites, k) for k in new_overs}
        overwrites.update(**new_overs)
        try:
            if channel.id not in self._channel_mutes:
                self._channel_mutes[channel.id] = {}
            self._channel_mutes[channel.id][user.id] = {
                "author": author.id,
                "member": user.id,
                "until": until.timestamp() if until else None,
            }
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
        except discord.Forbidden:
            del self._channel_mutes[channel.id][user.id]
            return {
                "success": False,
                "channel": channel,
                "reason": _(mute_unmute_issues["permissions_issue"]),
            }
        except discord.NotFound as e:
            if e.code == 10003:
                del self._channel_mutes[channel.id][user.id]
                return {
                    "success": False,
                    "channel": channel,
                    "reason": _(mute_unmute_issues["unknown_channel"]),
                }
            elif e.code == 10009:
                del self._channel_mutes[channel.id][user.id]
                return {
                    "success": False,
                    "channel": channel,
                    "reason": _(mute_unmute_issues["left_guild"]),
                }
        return {"success": True, "channel": channel, "old_overs": old_overs}

    async def channel_unmute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        reason: Optional[str] = None,
    ) -> Dict[str, Optional[Union[discord.abc.GuildChannel, str, bool]]]:
        overwrites = channel.overwrites_for(user)
        perms_cache = await self.config.member(user).perms_cache()

        _temp = None  # used to keep the cache incase we have permissions issues
        if channel.id in perms_cache:
            old_values = perms_cache[channel.id]
        else:
            old_values = {"send_messages": None, "add_reactions": None, "speak": None}

        if not await is_allowed_by_hierarchy(self.bot, self.config, guild, author, user):
            return {
                "success": False,
                "channel": channel,
                "reason": _(mute_unmute_issues["hierarchy_problem"]),
            }

        overwrites.update(**old_values)
        try:
            if overwrites.is_empty():
                await channel.set_permissions(
                    user, overwrite=cast(discord.PermissionOverwrite, None), reason=reason
                )
            else:
                await channel.set_permissions(user, overwrite=overwrites, reason=reason)
            if channel.id in self._channel_mutes and user.id in self._channel_mutes[channel.id]:
                _temp = copy(self._channel_mutes[channel.id][user.id])
                del self._channel_mutes[channel.id][user.id]
        except discord.Forbidden:
            if channel.id in self._channel_mutes and _temp:
                self._channel_mutes[channel.id][user.id] = _temp
            return {
                "success": False,
                "channel": channel,
                "reason": _(mute_unmute_issues["permissions_issue"]),
            }
        except discord.NotFound as e:
            if e.code == 10003:
                if channel.id in self._channel_mutes and _temp:
                    self._channel_mutes[channel.id][user.id] = _temp
                return {
                    "success": False,
                    "channel": channel,
                    "reason": _(mute_unmute_issues["unknown_channel"]),
                }
            elif e.code == 10009:
                if channel.id in self._channel_mutes and _temp:
                    self._channel_mutes[channel.id][user.id] = _temp
                return {
                    "success": False,
                    "channel": channel,
                    "reason": _(mute_unmute_issues["left_guild"]),
                }
        return {"success": True, "channel": channel, "reason": None}
