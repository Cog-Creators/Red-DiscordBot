import asyncio
import contextlib
import datetime
import time
import traceback

import discord
import lavalink

from redbot.core import commands
from redbot.core.utils.chat_formatting import inline

from ..abc import MixinMeta
from ..utils import CompositeMetaClass, _
from ...apis.playlist_interface import get_playlist, Playlist, delete_playlist
from ...audio_globals import get_playlist_api_wrapper
from ...errors import DatabaseError
from ...utils import rgetattr, get_track_description, PlaylistScope, track_to_json


class Listeners(MixinMeta, metaclass=CompositeMetaClass):
    async def cog_before_invoke(self, ctx: commands.Context):
        await self._ready_event.wait()
        # check for unsupported arch
        # Check on this needs refactoring at a later date
        # so that we have a better way to handle the tasks
        if self.llsetup in [ctx.command, ctx.command.root_parent]:
            pass

        elif self._connect_task and self._connect_task.cancelled():
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

    async def cog_after_invoke(self, ctx: commands.Context):
        await self._process_db(ctx)

    async def cog_command_error(self, ctx: commands.Context, error):
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
            await self.api_interface.run_tasks(ctx)
            message = "Error in command '{}'. Check your console or logs for details.".format(
                ctx.command.qualified_name
            )
            await ctx.send(inline(message))
            exception_log = "Exception in command '{}'\n" "".format(ctx.command.qualified_name)
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            self.bot._last_exception = exception_log

        await ctx.bot.on_command_error(
            ctx, getattr(error, "original", error), unhandled_by_cog=True
        )

    def cog_unload(self):
        if not self._cleaned_up:
            self.bot.dispatch("red_audio_unload", self)
            self._session.detach()
            self.bot.loop.create_task(self._close_database())
            if self._disconnect_task:
                self._disconnect_task.cancel()

            if self._connect_task:
                self._connect_task.cancel()

            if self._init_task:
                self._init_task.cancel()

            lavalink.unregister_event_listener(self.event_handler)
            self.bot.loop.create_task(lavalink.close())
            if self._manager is not None:
                self.bot.loop.create_task(self._manager.shutdown())

            self._cleaned_up = True

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        await self._ready_event.wait()
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild].remove(member.id)
            except (ValueError, KeyError, AttributeError):
                pass

    async def event_handler(
        self, player: lavalink.Player, event_type: lavalink.LavalinkEvents, extra
    ):
        current_track = player.current
        current_channel = player.channel
        guild = rgetattr(current_channel, "guild", None)
        guild_id = rgetattr(guild, "id", None)
        current_requester = rgetattr(current_track, "requester", None)
        current_stream = rgetattr(current_track, "is_stream", None)
        current_length = rgetattr(current_track, "length", None)
        current_thumbnail = rgetattr(current_track, "thumbnail", None)
        current_extras = rgetattr(current_track, "extras", {})
        guild_data = await self.config.guild(guild).all()
        repeat = guild_data["repeat"]
        notify = guild_data["notify"]
        disconnect = guild_data["disconnect"]
        autoplay = guild_data["auto_play"]
        description = get_track_description(current_track)
        status = await self.config.status()

        await self.error_reset(player)

        if event_type == lavalink.LavalinkEvents.TRACK_START:
            self.skip_votes[guild] = []
            playing_song = player.fetch("playing_song")
            requester = player.fetch("requester")
            player.store("prev_song", playing_song)
            player.store("prev_requester", requester)
            player.store("playing_song", current_track)
            player.store("requester", current_requester)
            self.bot.dispatch("red_audio_track_start", guild, current_track, current_requester)
        if event_type == lavalink.LavalinkEvents.TRACK_END:
            prev_song = player.fetch("prev_song")
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch("red_audio_track_end", guild, prev_song, prev_requester)
        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            prev_song = player.fetch("prev_song")
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch("red_audio_queue_end", guild, prev_song, prev_requester)
            if autoplay and not player.queue and player.fetch("playing_song") is not None:
                try:
                    await self.api_interface.autoplay(player)
                except DatabaseError:
                    notify_channel = player.fetch("channel")
                    if notify_channel:
                        notify_channel = self.bot.get_channel(notify_channel)
                        await self._embed_msg(
                            notify_channel, title=_("Couldn't get a valid track.")
                        )
                    return
        if event_type == lavalink.LavalinkEvents.TRACK_START and notify:
            notify_channel = player.fetch("channel")
            prev_song = player.fetch("prev_song")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                if player.fetch("notify_message") is not None:
                    with contextlib.suppress(discord.HTTPException):
                        await player.fetch("notify_message").delete()

                if (
                    autoplay
                    and current_extras.get("autoplay")
                    and (
                        prev_song is None
                        or (hasattr(prev_song, "extras") and not prev_song.extras.get("autoplay"))
                    )
                ):
                    await self._embed_msg(notify_channel, title=_("Auto Play Started."))

                if not description:
                    return
                if current_stream:
                    dur = "LIVE"
                else:
                    dur = lavalink.utils.format_time(current_length)

                thumb = None
                if await self.config.guild(guild).thumbnail() and current_thumbnail:
                    thumb = current_thumbnail

                notify_message = await self._embed_msg(
                    notify_channel,
                    title=_("Now Playing"),
                    description=description,
                    footer=_("Track length: {length} | Requested by: {user}").format(
                        length=dur, user=current_requester
                    ),
                    thumbnail=thumb,
                )
                player.store("notify_message", notify_message)
        if event_type == lavalink.LavalinkEvents.TRACK_START and status:
            player_check = await self._players_check()
            await self._status_check(*player_check)

        if event_type == lavalink.LavalinkEvents.TRACK_END and status:
            await asyncio.sleep(1)
            if not player.is_playing:
                player_check = await self._players_check()
                await self._status_check(*player_check)

        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            if not autoplay:
                notify_channel = player.fetch("channel")
                if notify_channel and notify:
                    notify_channel = self.bot.get_channel(notify_channel)
                    await self._embed_msg(notify_channel, title=_("Queue Ended."))
                if disconnect:
                    self.bot.dispatch("red_audio_audio_disconnect", guild)
                    await player.disconnect()
            if status:
                player_check = await self._players_check()
                await self._status_check(*player_check)

        if event_type in [
            lavalink.LavalinkEvents.TRACK_EXCEPTION,
            lavalink.LavalinkEvents.TRACK_STUCK,
        ]:
            message_channel = player.fetch("channel")
            while True:
                if current_track in player.queue:
                    player.queue.remove(current_track)
                else:
                    break
            if repeat:
                player.current = None
            if not guild_id:
                return
            self._error_counter.setdefault(guild_id, 0)
            if guild_id not in self._error_counter:
                self._error_counter[guild_id] = 0
            early_exit = await self.increase_error_counter(player)
            if early_exit:
                self._disconnected_players[guild_id] = True
                self.play_lock[guild_id] = False
                eq = player.fetch("eq")
                player.queue = []
                player.store("playing_song", None)
                if eq:
                    await self.config.custom("EQUALIZER", guild_id).eq_bands.set(eq.bands)
                await player.stop()
                await player.disconnect()
                self.bot.dispatch("red_audio_audio_disconnect", guild)
            if message_channel:
                message_channel = self.bot.get_channel(message_channel)
                if early_exit:
                    embed = discord.Embed(
                        colour=(await self.bot.get_embed_color(message_channel)),
                        title=_("Multiple errors detected"),
                        description=_(
                            "Closing the audio player "
                            "due to multiple errors being detected. "
                            "If this persists, please inform the bot owner "
                            "as the Audio cog may be temporally unavailable."
                        ),
                    )
                    return await message_channel.send(embed=embed)
                else:
                    description = description or ""
                    if event_type == lavalink.LavalinkEvents.TRACK_STUCK:
                        embed = discord.Embed(
                            title=_("Track Stuck"), description="{}".format(description)
                        )
                    else:
                        embed = discord.Embed(
                            title=_("Track Error"),
                            description="{}\n{}".format(extra.replace("\n", ""), description),
                        )
                    await message_channel.send(embed=embed)
            await player.skip()

    @commands.Cog.listener()
    async def on_red_audio_track_start(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member
    ):
        daily_cache = self._daily_playlist_cache.setdefault(
            guild.id, await self.config.guild(guild).daily_playlists()
        )
        scope = PlaylistScope.GUILD.value
        today = datetime.date.today()
        midnight = datetime.datetime.combine(today, datetime.datetime.min.time())
        track_identifier = track.track_identifier
        if daily_cache:
            name = f"Daily playlist - {today}"
            today_id = int(time.mktime(today.timetuple()))
            track = track_to_json(track)
            try:
                playlist = await get_playlist(
                    playlist_number=today_id,
                    scope=PlaylistScope.GUILD.value,
                    bot=self.bot,
                    guild=guild,
                    author=self.bot.user,
                )
            except RuntimeError:
                playlist = None

            if playlist:
                tracks = playlist.tracks
                tracks.append(track)
                await playlist.edit({"tracks": tracks})
            else:
                playlist = Playlist(
                    bot=self.bot,
                    scope=scope,
                    author=self.bot.user.id,
                    playlist_id=today_id,
                    name=name,
                    playlist_url=None,
                    tracks=[track],
                    guild=guild,
                )
                await playlist.save()

        with contextlib.suppress(Exception):
            too_old = midnight - datetime.timedelta(days=8)
            too_old_id = int(time.mktime(too_old.timetuple()))
            await delete_playlist(
                scope=scope, playlist_id=too_old_id, guild=guild, author=self.bot.user
            )

    @commands.Cog.listener()
    async def on_red_audio_queue_end(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member
    ):
        await self.api_interface.local_cache_api.youtube.clean_up_old_entries()
        await asyncio.sleep(5)
        dat = get_playlist_api_wrapper()
        if dat:
            await dat.delete_scheduled()
            await asyncio.sleep(5)
