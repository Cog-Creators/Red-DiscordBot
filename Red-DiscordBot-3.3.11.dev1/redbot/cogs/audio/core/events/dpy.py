import asyncio
import logging
import re
from pathlib import Path
from typing import Final, Pattern

import discord
import lavalink
from aiohttp import ClientConnectorError

from redbot.core import commands

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass, _
from ...audio_logging import debug_exc_log
from ...errors import TrackEnqueueError

log = logging.getLogger("red.cogs.Audio.cog.Events.dpy")

RE_CONVERSION: Final[Pattern] = re.compile('Converting to "(.*)" failed for parameter "(.*)".')


class DpyEvents(MixinMeta, metaclass=CompositeMetaClass):
    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        await self.cog_ready_event.wait()
        # check for unsupported arch
        # Check on this needs refactoring at a later date
        # so that we have a better way to handle the tasks
        if self.command_llsetup in [ctx.command, ctx.command.root_parent]:
            pass

        elif self.lavalink_connect_task and self.lavalink_connect_task.cancelled():
            await ctx.send(
                _(
                    "You have attempted to run Audio's Lavalink server on an unsupported"
                    " architecture. Only settings related commands will be available."
                )
            )
            raise RuntimeError(
                "Not running audio command due to invalid machine architecture for Lavalink."
            )
        # with contextlib.suppress(Exception):
        #     player = lavalink.get_player(ctx.guild.id)
        #     notify_channel = player.fetch("channel")
        #     if not notify_channel:
        #         player.store("channel", ctx.channel.id)
        self._daily_global_playlist_cache.setdefault(
            self.bot.user.id, await self.config.daily_playlists()
        )
        if self.local_folder_current_path is None:
            self.local_folder_current_path = Path(await self.config.localpath())
        if not ctx.guild:
            return
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        self._daily_playlist_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).daily_playlists()
        )
        if dj_enabled:
            dj_role = self._dj_role_cache.setdefault(
                ctx.guild.id, await self.config.guild(ctx.guild).dj_role()
            )
            dj_role_obj = ctx.guild.get_role(dj_role)
            if not dj_role_obj:
                await self.config.guild(ctx.guild).dj_enabled.set(None)
                self._dj_status_cache[ctx.guild.id] = None
                await self.config.guild(ctx.guild).dj_role.set(None)
                self._dj_role_cache[ctx.guild.id] = None
                await self.send_embed_msg(ctx, title=_("No DJ role found. Disabling DJ mode."))

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        await self.maybe_run_pending_db_tasks(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        error = getattr(error, "original", error)
        handled = False
        if isinstance(error, commands.ArgParserFailure):
            handled = True
            msg = _("`{user_input}` is not a valid value for `{command}`").format(
                user_input=error.user_input, command=error.cmd,
            )
            if error.custom_help_msg:
                msg += f"\n{error.custom_help_msg}"
            await self.send_embed_msg(
                ctx, title=_("Unable To Parse Argument"), description=msg, error=True,
            )
            if error.send_cmd_help:
                await ctx.send_help()
        elif isinstance(error, commands.ConversionFailure):
            handled = True
            if error.args:
                if match := RE_CONVERSION.search(error.args[0]):
                    await self.send_embed_msg(
                        ctx,
                        title=_("Invalid Argument"),
                        description=_(
                            "The argument you gave for `{}` is not valid: I was expecting a `{}`."
                        ).format(match.group(2), match.group(1)),
                        error=True,
                    )
                else:
                    await self.send_embed_msg(
                        ctx, title=_("Invalid Argument"), description=error.args[0], error=True,
                    )
            else:
                await ctx.send_help()
        elif isinstance(error, (IndexError, ClientConnectorError)) and any(
            e in str(error).lower() for e in ["no nodes found.", "cannot connect to host"]
        ):
            handled = True
            await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_("Connection to Lavalink has been lost."),
                error=True,
            )
            debug_exc_log(log, error, "This is a handled error")
        elif isinstance(error, KeyError) and "such player for that guild" in str(error):
            handled = True
            await self.send_embed_msg(
                ctx,
                title=_("No Player Available"),
                description=_("The bot is not connected to a voice channel."),
                error=True,
            )
            debug_exc_log(log, error, "This is a handled error")
        elif isinstance(error, (TrackEnqueueError, asyncio.exceptions.TimeoutError)):
            handled = True
            await self.send_embed_msg(
                ctx,
                title=_("Unable to Get Track"),
                description=_(
                    "I'm unable to get a track from Lavalink at the moment, "
                    "try again in a few minutes."
                ),
                error=True,
            )
            debug_exc_log(log, error, "This is a handled error")
        if not isinstance(
            error,
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.DisabledCommand,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
            ),
        ):
            self.update_player_lock(ctx, False)
            if self.api_interface is not None:
                await self.api_interface.run_tasks(ctx)
        if not handled:
            await self.bot.on_command_error(ctx, error, unhandled_by_cog=True)

    def cog_unload(self) -> None:
        if not self.cog_cleaned_up:
            self.bot.dispatch("red_audio_unload", self)
            self.session.detach()
            self.bot.loop.create_task(self._close_database())
            if self.player_automated_timer_task:
                self.player_automated_timer_task.cancel()

            if self.lavalink_connect_task:
                self.lavalink_connect_task.cancel()

            if self.cog_init_task:
                self.cog_init_task.cancel()

            lavalink.unregister_event_listener(self.lavalink_event_handler)
            self.bot.loop.create_task(lavalink.close())
            if self.player_manager is not None:
                self.bot.loop.create_task(self.player_manager.shutdown())

            self.cog_cleaned_up = True

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        if await self.bot.cog_disabled_in_guild(self, member.guild):
            return
        await self.cog_ready_event.wait()
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild].remove(member.id)
            except (ValueError, KeyError, AttributeError):
                pass
