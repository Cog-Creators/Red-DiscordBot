import asyncio
import contextlib
import discord
import logging

from abc import ABC
from typing import cast, Optional, Dict, List, Tuple, Literal, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from redbot.core.bot import Red
from redbot.core import commands, i18n, modlog, Config
from redbot.core.utils import AsyncIter, bounded_gather
from redbot.core.utils.chat_formatting import bold, humanize_timedelta, humanize_list, pagify
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

T_ = i18n.Translator("Mutes", __file__)

_ = lambda s: s

MUTE_UNMUTE_ISSUES = {
    "already_muted": _("That user is already muted in this channel."),
    "already_unmuted": _("That user is not muted in this channel."),
    "hierarchy_problem": _(
        "I cannot let you do that. You are not higher than the user in the role hierarchy."
    ),
    "assigned_role_hierarchy_problem": _(
        "I cannot let you do that. You are not higher than the mute role in the role hierarchy."
    ),
    "is_admin": _("That user cannot be (un)muted, as they have the Administrator permission."),
    "permissions_issue_role": _(
        "Failed to mute or unmute user. I need the Manage Roles "
        "permission and the user I'm muting must be "
        "lower than myself in the role hierarchy."
    ),
    "permissions_issue_channel": _(
        "Failed to mute or unmute user. I need the Manage Permissions permission."
    ),
    "left_guild": _("The user has left the server while applying an overwrite."),
    "unknown_channel": _("The channel I tried to mute or unmute the user in isn't found."),
    "role_missing": _("The mute role no longer exists."),
    "voice_mute_permission": _(
        "Because I don't have the Move Members permission, this will take into effect when the user rejoins."
    ),
}
_ = T_

log = logging.getLogger("red.mutes")

__all__ = [
    "Mutes",
    "mute_user",
    "unmute_user",
    "channel_mute_user",
    "channel_unmute_user",
    "MutedUser",
    "ChannelMutedUser",
    "check_for_mute_role",
    "is_mutes_disabled",
]

__version__ = "1.0.0"


@dataclass
class HasMutedUser:
    """
    This is a dataclass to represent whether or not a user
    has been muted in the server.

    Attributes
    ----------
        success: bool
            Whether or not the mute was a success.
        reason: Optional[str]
            The Optional reason for why the mute was not successful.
        channels: List[Tuple[discord.abc.GuildChannel, str]]
            The channels and reason for why the user could not be muted
            in those channels.
        user: discord.Member
            The user who was requested to be muted.
    """

    success: bool
    reason: Optional[str]
    channels: List[Tuple[discord.abc.GuildChannel, str]]
    user: discord.Member


@dataclass
class HasChannelMutedUser:
    """
    This is a dataclass to represent whether or not a user
    has been muted in the channel.

    Attributes
    ----------
        success: bool
            Whether or not the channel mute was a success.
        reason: Optional[str]
            The optional reason for why the mute was not successful.
        channel: discord.abc.GuildChannel
            The channel the user was requested to be muted in.
        user: discord.Member
            The user who was requested to be muted.
        old_overs: Optional[Dict[str, bool]]
            The overwrites for the user in the channel before muting.
    """

    success: bool
    reason: Optional[str]
    channel: discord.abc.GuildChannel
    user: discord.Member
    old_overs: Optional[Dict[str, bool]]


@dataclass
class MutedUser:
    """
    This is a datclass to represent a muted user in a server

    Attributes
    ----------
        guild_id: int
            The guild ID in which this MutedUser belongs.
        author_id: int
            The member ID of the moderator who requested the mute.
        user_id: int
            The member ID of the user who was muted.
        until: int
            The timestamp until the mute should be over.
        reason: Optional[str]
            The optional reason for the mute.
    """

    guild_id: int
    author_id: int
    user_id: int
    until: Optional[int]
    reason: Optional[str]


@dataclass
class ChannelMutedUser:
    """
    This is a datclass to represent a muted user in a server

    Attributes
    ----------
        guild_id: int
            The guild ID in which this MutedUser belongs.
        channel_id: int
            The channel ID in which the user was muted in.
        author_id: int
            The member ID of the moderator who requested the mute.
        user_id: int
            The member ID of the user who was muted.
        until: int
            The timestamp until the mute should be over.
        reason: Optional[str]
            The optional reason for the mute.
    """

    guild_id: int
    channel_id: int
    author_id: int
    user_id: int
    until: Optional[int]
    reason: Optional[str]


async def mute_user(
    bot: Red,
    *,
    guild: discord.Guild,
    author: discord.Member,
    user: discord.Member,
    until: Optional[datetime] = None,
    reason: Optional[str] = None,
) -> HasMutedUser:
    """
    Handles muting a user inside a server

    Parameters
    ----------
        bot: Red
            The bot object
        guild: discord.Guild
            The guild requesting the mute.
        author: discord.Member
            The member requesting the mute.
        user: discord.Member
            The member requesting to be muted.
        until: Optional[datetime]
            The optional datetime of when the mute should be over.
        reason: Optional[str]
            The optional reason for which the mute is occuring.

    Returns
    -------
        MutedUser:
            An object containing the success of the mute and reasons why
            the mute may not have been successful.

    """
    return await bot._mutes.mute_user(guild, author, user, until, reason)


async def unmute_user(
    bot: Red,
    *,
    guild: discord.Guild,
    author: discord.Member,
    user: discord.Member,
    reason: Optional[str] = None,
) -> HasMutedUser:
    """
    Handles muting a user inside a server

    Parameters
    ----------
        bot: Red
            The bot object
        guild: discord.Guild
            The guild requesting the mute.
        author: discord.Member
            The member requesting the mute.
        user: discord.Member
            The member requesting to be muted.
        until: Optional[datetime]
            The optional datetime of when the mute should be over.
        reason: Optional[str]
            The optional reason for which the mute is occuring.

    Returns
    -------
        MutedUser:
            An object containing the success of the mute and reasons why
            the mute may not have been successful.

    """
    return await bot._mutes.unmute_user(guild, author, user, reason)


async def channel_mute_user(
    bot: Red,
    *,
    guild: discord.Guild,
    channel: discord.abc.GuildChannel,
    author: discord.Member,
    user: discord.Member,
    until: Optional[datetime] = None,
    reason: Optional[str] = None,
) -> HasChannelMutedUser:
    """
    Handles muting a user in a channel

    Parameters
    ----------
        bot: Red
            The bot object
        guild: discord.Guild
            The guild requesting the mute.
        channel: discord.abc.GuildChannel
            The channel in which the user should be muted.
        author: discord.Member
            The member requesting the mute.
        user: discord.Member
            The member requesting to be muted.
        until: Optional[datetime]
            The optional datetime of when the mute should be over.
        reason: Optional[str]
            The optional reason for which the mute is occuring.

    Returns
    -------
        MutedUser:
            An object containing the success of the mute and reasons why
            the mute may not have been successful.

    """
    return await bot._mutes.channel_mute_user(guild, channel, author, user, until, reason)


async def channel_unmute_user(
    bot: Red,
    *,
    guild: discord.Guild,
    channel: discord.abc.GuildChannel,
    author: discord.Member,
    user: discord.Member,
    reason: Optional[str] = None,
) -> HasChannelMutedUser:
    """
    Handles muting a user inside a server

    Parameters
    ----------
        bot: Red
            The bot object
        guild: discord.Guild
            The guild requesting the mute.
        channel: discord.abc.GuildChannel
            The channel in which the user should be unmuted.
        author: discord.Member
            The member requesting the mute.
        user: discord.Member
            The member requesting to be muted.
        until: Optional[datetime]
            The optional datetime of when the mute should be over.
        reason: Optional[str]
            The optional reason for which the mute is occuring.

    Returns
    -------
        MutedUser:
            An object containing the success of the mute and reasons why
            the mute may not have been successful.

    """
    return await bot._mutes.channel_unmute_user(guild, channel, author, user, reason)


async def check_for_mute_role(bot: Red, ctx: commands.Context) -> bool:
    """
    This explains to the user whether or not mutes are setup correctly for
    automatic unmutes.
    """
    return await bot._mutes._check_for_mute_role(ctx)


async def is_mutes_disabled(bot: Red) -> bool:
    """
    Returns whether or not the Mutes API is enabled on the bot
    """
    return await bot._mutes.config.disabled()


async def get_server_mutes(bot: Red, ctx: commands.Context) -> Optional[Dict[int, MutedUser]]:
    if ctx.guild.id in bot._mutes._server_mutes:
        return bot._mutes._server_mutes[ctx.guild.id]
    return None


async def send_mute_dm_notification(
    bot: Red,
    user: Union[discord.User, discord.Member],
    moderator: Optional[Union[discord.User, discord.Member]],
    guild: discord.Guild,
    mute_type: str,
    reason: Optional[str],
    duration: Optional[datetime] = None,
):
    return await bot._mutes._send_dm_notification(
        user, moderator, guild, mute_type, reason, duration
    )


class Mutes:
    """
    Mute users temporarily or indefinitely.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(None, 49615220001, cog_name="Mutes", force_registration=True)
        default_guild = {
            "sent_instructions": False,
            "mute_role": None,
            "notification_channel": None,
            "muted_users": {},
            "default_time": 0,
            "dm": False,
            "show_mod": False,
        }
        self.config.register_global(force_role_mutes=True, schema_version=0, disabled=False)
        # Tbh I would rather force everyone to use role mutes.
        # I also honestly think everyone would agree they're the
        # way to go. If for whatever reason someone wants to
        # enable channel overwrite mutes for their bot they can.
        # Channel overwrite logic still needs to be in place
        # for channel mutes methods.
        self.config.register_guild(**default_guild)
        self.config.register_member(perms_cache={})
        self.config.register_channel(muted_users={})
        self._server_mutes: Dict[int, Dict[int, dict]] = {}
        self._channel_mutes: Dict[int, Dict[int, dict]] = {}
        self._unmute_tasks: Dict[str, asyncio.Task] = {}
        self._unmute_task = None
        self.mute_role_cache: Dict[int, int] = {}
        self._channel_mute_events: Dict[int, asyncio.Event] = {}
        # this is a dict of guild ID's and asyncio.Events
        # to wait for a guild to finish channel unmutes before
        # checking for manual overwrites

        self._init_task = self.bot.loop.create_task(self._initialize())

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

        all_members = await self.config.all_members()
        for g_id, data in all_members.items():
            for m_id, mutes in data.items():
                if m_id == user_id:
                    await self.config.member_from_ids(g_id, m_id).clear()

    async def _initialize(self):
        await self.bot.wait_until_red_ready()
        await self._maybe_update_config()
        if await self.config.disabled():
            return
        guild_data = await self.config.all_guilds()
        for g_id, mutes in guild_data.items():
            self._server_mutes[g_id] = {}
            if mutes["mute_role"]:
                self.mute_role_cache[g_id] = mutes["mute_role"]
            for user_id, mute in mutes["muted_users"].items():
                self._server_mutes[g_id][int(user_id)] = mute
        channel_data = await self.config.all_channels()
        for c_id, mutes in channel_data.items():
            self._channel_mutes[c_id] = {}
            for user_id, mute in mutes["muted_users"].items():
                self._channel_mutes[c_id][int(user_id)] = mute
        self._unmute_task = asyncio.create_task(self._handle_automatic_unmute())
        self.bot.add_listener(self.on_member_update)
        self.bot.add_listener(self.on_guild_channel_update)
        self.bot.add_listener(self.on_member_join)

    async def _maybe_update_config(self):
        schema_version = await self.config.schema_version()

        if schema_version == 0:
            await self._schema_0_to_1()
            schema_version += 1
            await self.config.schema_version.set(schema_version)

    async def _schema_0_to_1(self):
        """This contains conversion that adds guild ID to channel mutes data."""
        all_channels = await self.config.all_channels()
        if not all_channels:
            return

        start = datetime.now()
        log.info(
            "Config conversion to schema_version 1 started. This may take a while to proceed..."
        )
        async for channel_id in AsyncIter(all_channels.keys()):
            try:
                if (channel := self.bot.get_channel(channel_id)) is None:
                    channel = await self.bot.fetch_channel(channel_id)
                async with self.config.channel_from_id(channel_id).muted_users() as muted_users:
                    for mute_id, mute_data in muted_users.items():
                        mute_data["guild"] = channel.guild.id
            except (discord.NotFound, discord.Forbidden):
                await self.config.channel_from_id(channel_id).clear()

        log.info(
            "Config conversion to schema_version 1 done. It took %s to proceed.",
            datetime.now() - start,
        )

    def cog_unload(self):
        self._init_task.cancel()
        self._unmute_task.cancel()
        for task in self._unmute_tasks.values():
            task.cancel()

    async def is_allowed_by_hierarchy(
        self, guild: discord.Guild, mod: discord.Member, user: discord.Member
    ):
        is_special = mod == guild.owner or await self.bot.is_owner(mod)
        return mod.top_role > user.top_role or is_special

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Used to handle the cache if a member manually has the muted role removed
        """
        guild = before.guild
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        if guild.id not in self.mute_role_cache:
            return
        should_save = False
        mute_role_id = self.mute_role_cache[guild.id]
        mute_role = guild.get_role(mute_role_id)
        if not mute_role:
            return
        b = set(before.roles)
        a = set(after.roles)
        roles_removed = list(b - a)
        roles_added = list(a - b)
        await i18n.set_contextual_locales_from_guild(self.bot, guild)
        if mute_role in roles_removed:
            # send modlog case for unmute and remove from cache
            if guild.id not in self._server_mutes:
                # they weren't a tracked mute so we can return early
                return
            if after.id in self._server_mutes[guild.id]:
                await modlog.create_case(
                    self.bot,
                    guild,
                    datetime.now(timezone.utc),
                    "sunmute",
                    after,
                    None,
                    _("Manually removed mute role"),
                )
                del self._server_mutes[guild.id][after.id]
                should_save = True
                await self._send_dm_notification(
                    after, None, guild, _("Server unmute"), _("Manually removed mute role")
                )
        elif mute_role in roles_added:
            # send modlog case for mute and add to cache
            if guild.id not in self._server_mutes:
                # initialize the guild in the cache to prevent keyerrors
                self._server_mutes[guild.id] = {}
            if after.id not in self._server_mutes[guild.id]:
                await modlog.create_case(
                    self.bot,
                    guild,
                    datetime.now(timezone.utc),
                    "smute",
                    after,
                    None,
                    _("Manually applied mute role"),
                )
                self._server_mutes[guild.id][after.id] = {
                    "author": None,
                    "member": after.id,
                    "until": None,
                }
                should_save = True
                await self._send_dm_notification(
                    after, None, guild, _("Server mute"), _("Manually applied mute role")
                )
        if should_save:
            await self.config.guild(guild).muted_users.set(self._server_mutes[guild.id])

    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        """
        This handles manually removing overwrites for a user that has been muted
        """
        if await self.bot.cog_disabled_in_guild(self, after.guild):
            return
        await i18n.set_contextual_locales_from_guild(self.bot, after.guild)
        if after.guild.id in self._channel_mute_events:
            await self._channel_mute_events[after.guild.id].wait()
        if after.id in self._channel_mutes:
            before_perms: Dict[int, Dict[str, Optional[bool]]] = {
                o.id: {name: attr for name, attr in p} for o, p in before.overwrites.items()
            }
            after_perms: Dict[int, Dict[str, Optional[bool]]] = {
                o.id: {name: attr for name, attr in p} for o, p in after.overwrites.items()
            }
            to_del: List[int] = []
            for user_id in self._channel_mutes[after.id].keys():
                send_messages = False
                speak = False
                if user_id in after_perms:
                    send_messages = (
                        after_perms[user_id]["send_messages"] is None
                        or after_perms[user_id]["send_messages"] is True
                    )
                    speak = (
                        after_perms[user_id]["speak"] is None
                        or after_perms[user_id]["speak"] is True
                    )
                # explicit is better than implicit :thinkies:
                if user_id in before_perms and (
                    user_id not in after_perms or any((send_messages, speak))
                ):
                    user = after.guild.get_member(user_id)
                    send_dm_notification = True
                    if not user:
                        send_dm_notification = False
                        user = discord.Object(id=user_id)
                    log.debug(f"{user} - {type(user)}")
                    to_del.append(user_id)
                    log.debug("creating case")
                    if isinstance(after, discord.VoiceChannel):
                        unmute_type = "vunmute"
                        notification_title = _("Voice unmute")
                    else:
                        unmute_type = "cunmute"
                        notification_title = _("Channel unmute")
                    if send_dm_notification:
                        await self._send_dm_notification(
                            user,
                            None,
                            after.guild,
                            notification_title,
                            _("Manually removed channel overwrites"),
                        )
                    await modlog.create_case(
                        self.bot,
                        after.guild,
                        datetime.now(timezone.utc),
                        unmute_type,
                        user,
                        None,
                        _("Manually removed channel overwrites"),
                        until=None,
                        channel=after,
                    )
                    log.debug("created case")
            if to_del:
                for u_id in to_del:
                    del self._channel_mutes[after.id][u_id]
                await self.config.channel(after).muted_users.set(self._channel_mutes[after.id])

    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        if await self.bot.cog_disabled_in_guild(self, guild):
            return
        mute_role = await self.config.guild(guild).mute_role()
        if not mute_role:
            # channel overwrite mutes would quickly allow a malicious
            # user to globally rate limit the bot therefore we are not
            # going to support re-muting users via channel overwrites
            return
        await i18n.set_contextual_locales_from_guild(self.bot, guild)
        if guild.id in self._server_mutes:
            if member.id in self._server_mutes[guild.id]:
                role = guild.get_role(mute_role)
                if not role:
                    return
                if self._server_mutes[guild.id][member.id]["until"]:
                    until = datetime.fromtimestamp(
                        self._server_mutes[guild.id][member.id]["until"]
                    )
                else:
                    until = None
                await self.mute_user(
                    guild, guild.me, member, until, _("Previously muted in this server.")
                )

    async def _handle_automatic_unmute(self):
        """This is the core task creator and loop
        for automatic unmutes

        A resolution of 30 seconds seems appropriate
        to allow for decent resolution on low timed
        unmutes and without being too busy on our event loop
        """
        await self.bot.wait_until_red_ready()
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
        """This is here to cleanup our tasks
        and log when we have something going wrong
        inside our tasks.
        """
        log.debug("Cleaning unmute tasks")
        is_debug = log.getEffectiveLevel() <= logging.DEBUG
        for task_id in list(self._unmute_tasks.keys()):
            task = self._unmute_tasks[task_id]

            if task.cancelled():
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
        """This is where the logic for role unmutes is taken care of"""
        log.debug("Checking server unmutes")
        for g_id in self._server_mutes:
            guild = self.bot.get_guild(g_id)
            if guild is None or await self.bot.cog_disabled_in_guild(self, guild):
                continue
            await i18n.set_contextual_locales_from_guild(self.bot, guild)
            for u_id in self._server_mutes[guild.id]:
                if self._server_mutes[guild.id][u_id]["until"] is None:
                    continue
                time_to_unmute = (
                    self._server_mutes[guild.id][u_id]["until"]
                    - datetime.now(timezone.utc).timestamp()
                )
                if time_to_unmute < 60.0:
                    task_name = f"server-unmute-{g_id}-{u_id}"
                    if task_name in self._unmute_tasks:
                        continue
                    log.debug(f"Creating task: {task_name}")
                    self._unmute_tasks[task_name] = asyncio.create_task(
                        self._auto_unmute_user(guild, self._server_mutes[guild.id][u_id])
                    )

    async def _auto_unmute_user(self, guild: discord.Guild, data: dict):
        """
        This handles role unmutes automatically

        Since channel overwrite mutes are handled under the separate
        _auto_channel_unmute_user methods here we don't
        need to worry about the dict response for message
        since only role based mutes get added here
        """
        delay = data["until"] - datetime.now(timezone.utc).timestamp()
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)

        member = guild.get_member(data["member"])
        author = guild.get_member(data["author"])
        if not member:
            async with self.config.guild(guild).muted_users() as muted_users:
                if str(data["member"]) in muted_users:
                    del muted_users[str(data["member"])]
            del self._server_mutes[guild.id][data["member"]]
            return
        success = await self.unmute_user(guild, author, member, _("Automatic unmute"))
        async with self.config.guild(guild).muted_users() as muted_users:
            if str(member.id) in muted_users:
                del muted_users[str(member.id)]
        if success["success"]:
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
            await self._send_dm_notification(
                member, author, guild, _("Server unmute"), _("Automatic unmute")
            )
        else:
            chan_id = await self.config.guild(guild).notification_channel()
            notification_channel = guild.get_channel(chan_id)
            if not notification_channel:
                return
            if not notification_channel.permissions_for(guild.me).send_messages:
                return
            error_msg = _(
                "I am unable to unmute {user} for the following reason:\n{reason}"
            ).format(user=member, reason=success["reason"])
            try:
                await notification_channel.send(error_msg)
            except discord.errors.Forbidden:
                log.info(error_msg)
                return

    async def _handle_channel_unmutes(self):
        """This is where the logic for handling channel unmutes is taken care of"""
        log.debug("Checking channel unmutes")
        multiple_mutes = {}
        for c_id, c_data in self._channel_mutes.items():
            for u_id in self._channel_mutes[c_id]:
                if (
                    not self._channel_mutes[c_id][u_id]
                    or not self._channel_mutes[c_id][u_id]["until"]
                ):
                    continue
                guild = self.bot.get_guild(self._channel_mutes[c_id][u_id]["guild"])
                if guild is None or await self.bot.cog_disabled_in_guild(self, guild):
                    continue
                time_to_unmute = (
                    self._channel_mutes[c_id][u_id]["until"]
                    - datetime.now(timezone.utc).timestamp()
                )
                if time_to_unmute < 60.0:
                    if guild not in multiple_mutes:
                        multiple_mutes[guild] = {}
                    if u_id not in multiple_mutes[guild]:
                        multiple_mutes[guild][u_id] = {c_id: self._channel_mutes[c_id][u_id]}
                    else:
                        multiple_mutes[guild][u_id][c_id] = self._channel_mutes[c_id][u_id]

        for guild, users in multiple_mutes.items():
            await i18n.set_contextual_locales_from_guild(self.bot, guild)
            for user, channels in users.items():
                if len(channels) > 1:
                    task_name = f"server-unmute-channels-{guild.id}-{user}"
                    if task_name in self._unmute_tasks:
                        continue
                    log.debug(f"Creating task: {task_name}")
                    member = guild.get_member(user)
                    self._unmute_tasks[task_name] = asyncio.create_task(
                        self._auto_channel_unmute_user_multi(member, guild, channels)
                    )

                else:
                    for channel, mute_data in channels.items():
                        task_name = f"channel-unmute-{channel}-{user}"
                        log.debug(f"Creating task: {task_name}")
                        if task_name in self._unmute_tasks:
                            continue
                        self._unmute_tasks[task_name] = asyncio.create_task(
                            self._auto_channel_unmute_user(guild.get_channel(channel), mute_data)
                        )

        del multiple_mutes

    async def _auto_channel_unmute_user_multi(
        self, member: discord.Member, guild: discord.Guild, channels: Dict[int, dict]
    ):
        """This is meant to handle multiple channels all being unmuted at once"""
        if guild.id in self._channel_mute_events:
            self._channel_mute_events[guild.id].clear()
        else:
            self._channel_mute_events[guild.id] = asyncio.Event()
        tasks = []
        for channel, mute_data in channels.items():
            author = guild.get_member(mute_data["author"])
            tasks.append(
                self._auto_channel_unmute_user(guild.get_channel(channel), mute_data, False)
            )
        results = await bounded_gather(*tasks)
        unmuted_channels = [guild.get_channel(c) for c in channels.keys()]
        for result in results:
            if not result:
                continue
            _mmeber, channel, reason = result
            unmuted_channels.remove(channel)
        modlog_reason = _("Automatic unmute")

        channel_list = humanize_list([c.mention for c in unmuted_channels if c is not None])
        if channel_list:
            modlog_reason += _("\nUnmuted in channels: ") + channel_list

        await modlog.create_case(
            self.bot,
            guild,
            datetime.now(timezone.utc),
            "sunmute",
            member,
            author,
            modlog_reason,
            until=None,
        )
        await self._send_dm_notification(
            member, author, guild, _("Server unmute"), _("Automatic unmute")
        )
        self._channel_mute_events[guild.id].set()
        if any(results):
            reasons = {}
            for result in results:
                if not result:
                    continue
                _member, channel, reason = result
                if reason not in reasons:
                    reasons[reason] = [channel]
                else:
                    reasons[reason].append(channel)
            error_msg = _("{member} could not be unmuted for the following reasons:\n").format(
                member=member
            )
            for reason, channel_list in reasons.items():
                error_msg += _("{reason} In the following channels: {channels}\n").format(
                    reason=reason,
                    channels=humanize_list([c.mention for c in channel_list]),
                )
            chan_id = await self.config.guild(guild).notification_channel()
            notification_channel = guild.get_channel(chan_id)
            if notification_channel is None:
                return None
            if not notification_channel.permissions_for(guild.me).send_messages:
                return None
            try:
                await notification_channel.send(error_msg)
            except discord.errors.Forbidden:
                log.info(error_msg)
                return None

    async def _auto_channel_unmute_user(
        self, channel: discord.abc.GuildChannel, data: dict, create_case: bool = True
    ) -> Optional[Tuple[discord.Member, discord.abc.GuildChannel, str]]:
        """This is meant to unmute a user in individual channels"""
        delay = data["until"] - datetime.now(timezone.utc).timestamp()
        if delay < 1:
            delay = 0
        await asyncio.sleep(delay)
        member = channel.guild.get_member(data["member"])
        author = channel.guild.get_member(data["author"])
        if not member:
            async with self.config.channel(channel).muted_users() as muted_users:
                if str(data["member"]) in muted_users:
                    del muted_users[str(data["member"])]
            if (
                channel.id in self._channel_mutes
                and data["member"] in self._channel_mutes[channel.id]
            ):
                del self._channel_mutes[channel.id][data["member"]]
            return None
        success = await self.channel_unmute_user(
            channel.guild, channel, author, member, _("Automatic unmute")
        )
        async with self.config.channel(channel).muted_users() as muted_users:
            if str(member.id) in muted_users:
                del muted_users[str(member.id)]
        if success["success"]:
            if create_case:
                if isinstance(channel, discord.VoiceChannel):
                    unmute_type = "vunmute"
                    notification_title = _("Voice unmute")
                else:
                    unmute_type = "cunmute"
                    notification_title = _("Channel unmute")
                await modlog.create_case(
                    self.bot,
                    channel.guild,
                    datetime.now(timezone.utc),
                    unmute_type,
                    member,
                    channel.guild.me,
                    _("Automatic unmute"),
                    until=None,
                    channel=channel,
                )
                await self._send_dm_notification(
                    member, author, channel.guild, notification_title, _("Automatic unmute")
                )
            return None
        else:
            error_msg = _(
                "I am unable to unmute {user} in {channel} for the following reason:\n{reason}"
            ).format(user=member, channel=channel.mention, reason=success["reason"])
            if create_case:
                chan_id = await self.config.guild(channel.guild).notification_channel()
                notification_channel = channel.guild.get_channel(chan_id)
                if not notification_channel:
                    return None
                if not notification_channel.permissions_for(channel.guild.me).send_messages:
                    return None
                try:
                    await notification_channel.send(error_msg)
                except discord.errors.Forbidden:
                    log.info(error_msg)
                    return None
            else:
                return (member, channel, success["reason"])

    async def _send_dm_notification(
        self,
        user: Union[discord.User, discord.Member],
        moderator: Optional[Union[discord.User, discord.Member]],
        guild: discord.Guild,
        mute_type: str,
        reason: Optional[str],
        duration=None,
    ):
        if not await self.config.guild(guild).dm():
            return

        show_mod = await self.config.guild(guild).show_mod()
        title = bold(mute_type)
        if duration:
            duration_str = humanize_timedelta(timedelta=duration)
            until = datetime.now(timezone.utc) + duration
            until_str = until.strftime("%Y-%m-%d %H:%M:%S UTC")

        if moderator is None:
            moderator_str = _("Unknown")
        else:
            moderator_str = str(moderator)

        if not reason:
            reason = _("No reason provided.")

        # okay, this is some poor API to require PrivateChannel here...
        if await self.bot.embed_requested(await user.create_dm(), user):
            em = discord.Embed(
                title=title,
                description=reason,
                color=await self.bot.get_embed_color(user),
            )
            em.timestamp = datetime.utcnow()
            if duration:
                em.add_field(name=_("Until"), value=until_str)
                em.add_field(name=_("Duration"), value=duration_str)
            em.add_field(name=_("Guild"), value=guild.name, inline=False)
            if show_mod:
                em.add_field(name=_("Moderator"), value=moderator_str)
            try:
                await user.send(embed=em)
            except discord.Forbidden:
                pass
        else:
            message = f"{title}\n>>> "
            message += reason
            message += (
                _("\n**Moderator**: {moderator}").format(moderator=moderator_str)
                if show_mod
                else ""
            )
            message += (
                _("\n**Until**: {until}\n**Duration**: {duration}").format(
                    until=until_str, duration=duration_str
                )
                if duration
                else ""
            )
            message += _("\n**Guild**: {guild_name}").format(guild_name=guild.name)
            try:
                await user.send(message)
            except discord.Forbidden:
                pass

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

    async def _check_for_mute_role(self, ctx: commands.Context) -> bool:
        """
        This explains to the user whether or not mutes are setup correctly for
        automatic unmutes.
        """
        command_1 = f"{ctx.clean_prefix}muteset role"
        command_2 = f"{ctx.clean_prefix}muteset makerole"
        msg = _(
            "This server does not have a mute role setup. "
            " You can setup a mute role with `{command_1}` or"
            "`{command_2}` if you just want a basic role created setup.\n\n"
        ).format(command_1=command_1, command_2=command_2)
        mute_role_id = await self.config.guild(ctx.guild).mute_role()
        mute_role = ctx.guild.get_role(mute_role_id)
        sent_instructions = await self.config.guild(ctx.guild).sent_instructions()
        force_role_mutes = await self.config.force_role_mutes()
        if force_role_mutes and not mute_role:
            await ctx.send(msg)
            return False

        if mute_role or sent_instructions:
            return True
        else:
            msg += _(
                "Channel overwrites for muting users can get expensive on Discord's API "
                "as such we recommend that you have an admin setup a mute role instead. "
                "Channel overwrites will also not re-apply on guild join, so a user "
                "who has been muted may leave and re-join and no longer be muted. "
                "Role mutes do not have this issue.\n\n"
                "Are you sure you want to continue with channel overwrites? "
            )
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

    async def mute_user(
        self,
        guild: discord.Guild,
        author: discord.Member,
        user: discord.Member,
        until: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> HasMutedUser:
        """
        Handles muting users
        """
        permissions = user.guild_permissions
        ret: HasMutedUser = HasMutedUser(False, None, [], user)
        # TODO: This typing is ugly and should probably be an object on its own
        # along with this entire method and some othe refactorization
        # v1.0.0 is meant to look ugly right :')
        if permissions.administrator:
            ret.reason = _(MUTE_UNMUTE_ISSUES["is_admin"])
            return ret
        if not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret
        mute_role = await self.config.guild(guild).mute_role()

        if mute_role:

            role = guild.get_role(mute_role)
            if not role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["role_missing"])
                return ret
            if author != guild.owner and role >= author.top_role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["assigned_role_hierarchy_problem"])
                return ret
            if not guild.me.guild_permissions.manage_roles or role >= guild.me.top_role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_role"])
                return ret
            # This is here to prevent the modlog case from happening on role updates
            # we need to update the cache early so it's there before we receive the member_update event
            if guild.id not in self._server_mutes:
                self._server_mutes[guild.id] = {}
            muted_user = MutedUser(
                author_id=author.id,
                user_id=user.id,
                guild_id=guild.id,
                reason=reason,
                until=int(until.timestamp()) if until else None,
            )
            self._server_mutes[guild.id][user.id] = muted_user
            try:
                await user.add_roles(role, reason=reason)
                await self.config.guild(guild).muted_users.set(self._server_mutes[guild.id])
            except discord.errors.Forbidden:
                if guild.id in self._server_mutes and user.id in self._server_mutes[guild.id]:
                    del self._server_mutes[guild.id][user.id]
                ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_role"])
                return ret
            ret.success = True
            return ret
        else:
            perms_cache = {}
            tasks = []
            for channel in guild.channels:
                tasks.append(self.channel_mute_user(guild, channel, author, user, until, reason))
            task_result = await bounded_gather(*tasks)
            for task in task_result:
                if not task.success:
                    ret.channels.append((task.channel, task.reason))
                else:
                    chan_id = task.channel.id
                    perms_cache[str(chan_id)] = task.old_overs
                    ret.success = True
            await self.config.member(user).perms_cache.set(perms_cache)
            return ret

    async def unmute_user(
        self,
        guild: discord.Guild,
        author: discord.Member,
        user: discord.Member,
        reason: Optional[str] = None,
    ) -> HasMutedUser:
        """
        Handles unmuting users
        """
        ret: MutedUser = MutedUser(False, None, [], user)
        mute_role = await self.config.guild(guild).mute_role()
        if not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret
        if mute_role:

            role = guild.get_role(mute_role)
            if not role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["role_missing"])
                return ret

            if guild.id in self._server_mutes:
                if user.id in self._server_mutes[guild.id]:
                    del self._server_mutes[guild.id][user.id]
            if not guild.me.guild_permissions.manage_roles or role >= guild.me.top_role:
                ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_role"])
                return ret
            try:
                await user.remove_roles(role, reason=reason)
            except discord.errors.Forbidden:
                ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_role"])
                return ret
            ret.success = True
            return ret
        else:
            tasks = []
            for channel in guild.channels:
                tasks.append(self.channel_unmute_user(guild, channel, author, user, reason))
            results = await bounded_gather(*tasks)
            for task in results:
                if not task.success:
                    ret.channels.append((task.channel, task.reason))
                else:
                    ret.success = True
            await self.config.member(user).clear()
            return ret

    async def channel_mute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        until: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> HasChannelMutedUser:
        """Mutes the specified user in the specified channel"""
        overwrites = channel.overwrites_for(user)
        permissions = channel.permissions_for(user)
        ret: HasChannelMutedUser = HasChannelMutedUser(False, None, channel, user, {})
        if permissions.administrator:
            ret.reason = _(MUTE_UNMUTE_ISSUES["is_admin"])
            return ret

        new_overs: dict = {}
        move_channel = False
        new_overs.update(send_messages=False, add_reactions=False, speak=False)
        send_reason = None
        if user.voice and user.voice.channel:
            if channel.permissions_for(guild.me).move_members:
                move_channel = True
            else:
                send_reason = _(MUTE_UNMUTE_ISSUES["voice_mute_permission"])

        if not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret

        old_overs = {k: getattr(overwrites, k) for k in new_overs}
        overwrites.update(**new_overs)
        if channel.id not in self._channel_mutes:
            self._channel_mutes[channel.id] = {}
        if user.id in self._channel_mutes[channel.id]:
            ret.reason = _(MUTE_UNMUTE_ISSUES["already_muted"])
            return ret
        if not channel.permissions_for(guild.me).manage_permissions:
            ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_channel"])
            return ret
        muted_user = ChannelMutedUser(
            guild_id=guild.id,
            channel_id=channel.id,
            author_id=author.id,
            user_id=user.id,
            until=int(until.timestamp()) if until else None,
            reason=reason,
        )
        self._channel_mutes[channel.id][user.id] = muted_user
        try:
            await channel.set_permissions(user, overwrite=overwrites, reason=reason)
            async with self.config.channel(channel).muted_users() as muted_users:
                muted_users[str(user.id)] = self._channel_mutes[channel.id][user.id]
        except discord.NotFound as e:
            if channel.id in self._channel_mutes and user.id in self._channel_mutes[channel.id]:
                del self._channel_mutes[channel.id][user.id]
            if e.code == 10003:
                if (
                    channel.id in self._channel_mutes
                    and user.id in self._channel_mutes[channel.id]
                ):
                    del self._channel_mutes[channel.id][user.id]
                ret.reason = _(MUTE_UNMUTE_ISSUES["unknown_channel"])
                return ret
            elif e.code == 10009:
                if (
                    channel.id in self._channel_mutes
                    and user.id in self._channel_mutes[channel.id]
                ):
                    del self._channel_mutes[channel.id][user.id]
                ret.reason = _(MUTE_UNMUTE_ISSUES["left_guild"])
                return ret
        if move_channel:
            try:
                await user.move_to(channel)
            except discord.HTTPException:
                # catch all discord errors because the result will be the same
                # we successfully muted by this point but can't move the user
                ret.reason = _(MUTE_UNMUTE_ISSUES["voice_mute_permission"])
                ret.old_overs = old_overs
                return ret
        ret.success = True
        ret.old_overs = old_overs
        ret.reason = send_reason
        return ret

    async def channel_unmute_user(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel,
        author: discord.Member,
        user: discord.Member,
        reason: Optional[str] = None,
    ) -> ChannelMutedUser:
        """Unmutes the specified user in a specified channel"""
        overwrites = channel.overwrites_for(user)
        perms_cache = await self.config.member(user).perms_cache()
        ret: ChannelMutedUser = ChannelMutedUser(False, None, channel, user, {})
        move_channel = False
        if channel.id in perms_cache:
            old_values = perms_cache[channel.id]
        else:
            old_values = {"send_messages": None, "add_reactions": None, "speak": None}

        if user.voice and user.voice.channel:
            if channel.permissions_for(guild.me).move_members:
                move_channel = True

        if not await self.is_allowed_by_hierarchy(guild, author, user):
            ret.reason = _(MUTE_UNMUTE_ISSUES["hierarchy_problem"])
            return ret

        overwrites.update(**old_values)
        if channel.id in self._channel_mutes and user.id in self._channel_mutes[channel.id]:
            del self._channel_mutes[channel.id][user.id]
        else:
            ret.reason = _(MUTE_UNMUTE_ISSUES["already_unmuted"])
            return ret
        if not channel.permissions_for(guild.me).manage_permissions:
            ret.reason = _(MUTE_UNMUTE_ISSUES["permissions_issue_channel"])
            return ret
        try:
            if overwrites.is_empty():
                await channel.set_permissions(
                    user, overwrite=cast(discord.PermissionOverwrite, None), reason=reason
                )
            else:
                await channel.set_permissions(user, overwrite=overwrites, reason=reason)
            async with self.config.channel(channel).muted_users() as muted_users:
                if str(user.id) in muted_users:
                    del muted_users[str(user.id)]
        except discord.NotFound as e:
            if e.code == 10003:
                ret.reason = _(MUTE_UNMUTE_ISSUES["unknown_channel"])
                return ret
            elif e.code == 10009:
                ret.reason = _(MUTE_UNMUTE_ISSUES["left_guild"])
                return ret
        if move_channel:
            try:
                await user.move_to(channel)
            except discord.HTTPException:
                # catch all discord errors because the result will be the same
                # we successfully muted by this point but can't move the user
                ret.reason = _(MUTE_UNMUTE_ISSUES["voice_mute_permission"])
                return ret
        ret.success = True
        return ret
