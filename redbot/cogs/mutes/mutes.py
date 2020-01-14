from __future__ import annotations

import asyncio
import logging
from datetime import timedelta, datetime
from typing import Awaitable, Dict, NamedTuple, Optional, Tuple, Union, no_type_check

import discord

from redbot.core import commands, checks, modlog
from redbot.core.commands import TimedeltaConverter
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.discord_helpers import OverwriteDiff
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.dbtools import APSWConnectionWrapper as Connection

from . import utils
from .errors import NoChangeError, PermError

TaskDict = Dict[Tuple[int, int], asyncio.Task]

_ = Translator("Mutes", __file__)
log = logging.getLogger("red.mutes")


@cog_i18n(_)
class Mutes(commands.Cog):
    """
    A cog to mute users with.
    """

    def __init__(self, bot):
        self.bot = bot
        self.conn = Connection(cog_data_path(self) / "mutes.db")
        self.config = Config.get_conf(self, identifier=240961564503441410)
        self.config.register_guild(
            mute_deny_text=2112,  # send, react
            mute_deny_voice=2097152,  # speak
            excluded_channel_ids=[],
        )
        self._unmute_task = asyncio.create_task(self.unmute_loop())
        self._task_queue = asyncio.Queue()
        self._server_unmute_tasks: TaskDict = {}
        self._channel_unmute_tasks: TaskDict = {}
        self._ready = asyncio.Event()
        self.bot.loop.create_task(self._cog_init())

    async def _cog_init(self):
        with self.conn.with_cursor() as cursor:
            cursor.execute("""PRAGMA journal_mode=wal""")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mutes(
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    allows_added INTEGER,
                    allows_removed INTEGER,
                    denies_added INTEGER,
                    denies_removed INTEGER,
                    expires_at INTEGER,
                    PRIMARY KEY (user_id, channel_id)
                );
                """
            )
        self._ready.set()

    async def cog_before_invoke(self):
        await self._ready.wait()

    def cog_unload(self):
        self.unmute_task.cancel()
        for task in self._server_unmute_tasks.values():
            task.cancel()
        for task in self._channel_unmute_tasks.values():
            task.cancel()

    def _clean_task_dict(self, task_dict):

        is_debug = log.getEffectiveLevel() <= logging.DEBUG

        for k in list(task_dict.keys()):
            task = task_dict[k]

            if task.canceled():
                task_dict.pop(k, None)
                continue

            if task.done():
                try:
                    r = task.result()
                except Exception:
                    # Log exception info for dead tasks, but only while debugging.
                    if is_debug:
                        log.exception("Dead server unmute task.")
                task_dict.pop(k, None)

    async def unmute_loop(self):
        await self.bot.wait_until_ready()
        while True:
            async with self._task_lock:
                self._clean_task_dict(self._server_unmute_tasks)
                self._clean_task_dict(self._channel_unmute_tasks)
                await self._schedule_unmutes(300)
            await asyncio.sleep(300)

    async def _schedule_unmutes(self, schedule_by_seconds: int = 300):
        """
        Schedules unmuting.
        Mutes get scheduled as tasks so that mute extensions or changes to make a mute
        permanent can have a scheduled mute be canceled.
        """
        raise NotImplementedError()  # TODO

    async def _cancel_channel_mute_delayed(self, *, delay: float, channel_id: int, member_id: int):
        """
        After a delay, attempt to unmute someone
        """
        raise NotImplementedError()  # TODO

    async def _cancel_server_mute_delayed(self, *, delay: float, guild_id: int, member_id: int):
        """
        After a delay, attempt to unmute someone.
        """
        await asyncio.sleep(delay)

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        member = guild.get_member(member_id)

        if not member:  # Still clear this to avoid re-muting on-join after expiration.
            pass

        # TODO

    @staticmethod
    async def channel_mute_with_diff(
        *,
        channel: discord.abc.GuildChannel,
        target: Union[discord.Role, discord.Member],
        deny_value: int,
        reason: Optional[str] = None,
    ) -> OverwriteDiff:
        """
        Parameters
        ----------
        channel : discord.abc.GuildChannel
        target : Union[discord.Role, discord.Member]
        deny_value : int
            The permissions values which should be denied.
        reason : str

        Returns
        -------
        OverwriteDiff

        Raises
        ------
        discord.Forbidden
            see `discord.abc.GuildChannel.set_permissions`
        discord.NotFound
            see `discord.abc.GuildChannel.set_permissions`
        discord.HTTPException
            see `discord.abc.GuildChannel.set_permissions`
        NoChangeError
            the edit was aborted due to no change
            in permissions between initial and requested
        """
        diff_to_apply = OverwriteDiff(denies_added=deny_value)
        start = channel.overwrites_for(target)
        new_overwrite = start + diff_to_apply
        result_diff = OverwriteDiff.from_overwrites(before=start, after=new_overwrite)

        if not result_diff:
            raise NoChangeError() from None

        await channel.set_permissions(target, overwrite=new_overwrite, reason=reason)
        return result_diff

    @staticmethod
    async def channel_unmute_from_diff(
        *,
        channel: discord.abc.GuildChannel,
        target: Union[discord.Role, discord.Member],
        diff: OverwriteDiff,
        reason: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        channel : discord.abc.GuildChannel
        target : Union[discord.Role, discord.Member]
        diff : OverwriteDiff
            The recorded difference from a prior mute to undo
        reason : str

        Raises
        ------
        discord.Forbidden
            see `discord.abc.GuildChannel.set_permissions`
        discord.NotFound
            see `discord.abc.GuildChannel.set_permissions`
        discord.HTTPException
            see `discord.abc.GuildChannel.set_permissions`
        NoChangeError
            the edit was aborted due to no change
            in permissions between initial and requested
        """

        start = channel.overwrites_for(target)
        new_overwrite = start - diff

        if start == new_overwrite:
            raise NoChangeError()

        await channel.set_permissions(target, overwrite=new_overwrite, reason=reason)

    async def do_command_server_mute(
        self,
        *,
        ctx: commands.Context,
        target: discord.Member,
        duration: Optional[timedelta] = None,
        reason: str,
    ):
        """
        This avoids duplicated logic with the option to use
        the command group as one of the commands itself.

        Parameters
        ----------
        ctx : commands.Context
            The context the command was invoked in
        target : discord.Member
            The person to mute
        duration : Optional[timedelta]
            If provided, the amount of time to mute the user for
        reason : str
            The reason for the mute

        """
        raise NotImplementedError()  # TODO

    async def apply_server_mute(
        self,
        *,
        target: Optional[discord.Member] = None,
        mod: discord.Member,
        duration: Optional[timedelta],
        reason: Optional[str] = None,
        target_id: Optional[int] = None,
    ):
        """
        Applies a mute server wide

        Parameters
        ----------
        target : Optional[discord.Member]
            The member to be muted. This can only be omitted if ``target_id`` is supplied.
        target_id : Optional[int]
            The member id to mute. This can only be omitted if ``target`` is supplied.
        mod : discord.Member
            The responisble moderator
        duration : Optional[timedelta]
            If provided, the mute is considered temporary, and should be scheduled
            for unmute after this period of time.
        reason : Optional[str]
            If provided, the reason for muting a user.
            
            This should be the reason from the moderator's perspective.
            All formatting should take place here.
            This should be less than 900 characters long.
            Longer reasons will be truncated.

        Returns
        -------
        ServerMuteResults
            A class which contains the mute results
            and some helpers for providing them to users.

        Raises
        ------
        NoChangeError
            If the server mute would result in zero changes.
        ValueError
            Raised if not given a target or target id, or if the target is not in the guild
        PermError
            Raised if we detect an invalid target or bot permissions.
            This error will contain a user-friendly error message.
        discord.Forbidden
            This will only be raised for 2FA related forbiddens, 
            or if the bot's allowed permissions change mid operation.
        discord.HTTPException
            Sometimes the API gives these back without a reason.
        """
        raise NotImplementedError()  # TODO

    async def do_command_server_unmute(
        self, *, ctx: commands.Context, target: discord.Member, reason: str
    ):
        """
        All actual command logic.
        """
        raise NotImplementedError()  # TODO

    async def do_command_channel_mute(
        self,
        *,
        ctx: commands.Context,
        target: discord.Member,
        channel: discord.abc.GuildChannel,
        duration: Optional[timedelta] = None,
        reason: str,
    ):
        """
        All actual command logic.
        """

    async def do_command_channel_unmute(
        self,
        *,
        ctx: commands.Context,
        target: discord.Member,
        channel: discord.abc.GuildChannel,
        reason: str,
    ):
        """
        All actual command logic.
        """
        raise NotImplementedError()  # TODO

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group()
    async def _muteset(self, ctx: commands.Context):
        """
        Allows configuring [botname]'s mute behavior.
        """
        pass

    @checks.mod()
    @commands.group(name="mute")
    @no_type_check
    async def mute_group(self, ctx):
        """
        Mutes users.
        """
        pass

    @checks.mod()
    @commands.group(name="tempmute")
    @no_type_check
    async def tempmute_group(
        self,
        ctx,
        target: discord.Member = None,
        duration: TimedeltaConverter = None,
        *,
        reason: str = None,
    ):
        """
        Mutes users, for some amount of time.
        """
        pass

    @checks.mod()
    @mute_group.command(name="channel")
    @no_type_check
    async def mute_channel(self, ctx, target: discord.Member, *, reason: str = ""):
        """
        Mutes a user in the current channel.
        """
        await self.do_command_channel_mute(
            ctx=ctx, target=target, reason=reason, channel=ctx.channel, duration=None
        )

    @checks.mod()
    @mute_group.command(name="server", aliases=["guild"])
    @no_type_check
    async def mute_server(self, ctx, target: discord.Member, *, reason: str = ""):
        """
        Mutes a user in the current server.
        """
        await self.do_command_server_mute(ctx=ctx, target=target, reason=reason, duration=None)

    @checks.mod()
    @tempmute_group.command(name="channel")
    @no_type_check
    async def tempmute_channel(
        self, ctx, target: discord.Member, duration: TimedeltaConverter, *, reason: str = ""
    ):
        """
        Mutes a user in the current channel.
        """
        await self.do_command_channel_mute(
            ctx=ctx, target=target, reason=reason, channel=ctx.channel, duration=duration
        )

    @checks.mod()
    @tempmute_group.command(name="server", aliases=["guild"])
    @no_type_check
    async def tempmute_server(
        self, ctx, target: discord.Member, duration: TimedeltaConverter, *, reason: str = ""
    ):
        """
        Mutes a user in the current server.
        """
        await self.do_command_server_mute(ctx=ctx, target=target, reason=reason, duration=duration)
