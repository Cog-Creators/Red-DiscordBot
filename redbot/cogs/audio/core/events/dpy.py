import logging

import discord
import lavalink

from redbot.core import commands
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass, _

log = logging.getLogger("red.cogs.Audio.cog.Events.dpy")


class DpyEvents(MixinMeta, metaclass=CompositeMetaClass):
    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        await self.cog_ready_event.wait()
        # check for unsupported arch
        # Check on this needs refactoring at a later date
        # so that we have a better way to handle the tasks
        if self._llsetup in [ctx.command, ctx.command.root_parent]:
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
                await self._embed_msg(ctx, title=_("No DJ role found. Disabling DJ mode."))

    async def cog_after_invoke(self, ctx: commands.Context) -> None:
        await self._process_db(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if not isinstance(
            getattr(error, "original", error),
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.DisabledCommand,
                commands.CommandOnCooldown,
            ),
        ):
            self._play_lock(ctx, False)
            if self.api_interface is not None:
                await self.api_interface.run_tasks(ctx)

        await ctx.bot.on_command_error(
            ctx, getattr(error, "original", error), unhandled_by_cog=True
        )

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
        await self.cog_ready_event.wait()
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild].remove(member.id)
            except (ValueError, KeyError, AttributeError):
                pass
