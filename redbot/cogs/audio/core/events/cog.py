import asyncio
import datetime
import logging
import time
import contextlib
from pathlib import Path

from typing import Optional

import discord
import lavalink

from redbot.core import commands, audio
from redbot.core.audio_utils.errors import DatabaseError, TrackEnqueueError, NotConnectedToVoice
from redbot.core.i18n import Translator

from ...apis.playlist_interface import Playlist, delete_playlist, get_playlist
from ...audio_logging import debug_exc_log
from ...utils import PlaylistScope
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Events.audio")
_ = Translator("Audio", Path(__file__))


class AudioEvents(MixinMeta, metaclass=CompositeMetaClass):
    @commands.Cog.listener()
    async def on_red_audio_track_start(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member
    ):
        if not guild:
            return

        try:
            player = audio._get_ll_player(guild)
        except NotConnectedToVoice:
            return

        guild_data = await self.config.guild(guild).all()
        global_data = await self.config.all()
        notify = guild_data["notify"]
        status = global_data["status"]
        self.skip_votes[guild.id] = set()

        notify_channel = player.fetch("notify_channel")
        if notify_channel and guild_data["auto_play"]:
            if [notify_channel, player.channel.id] != guild_data["currently_auto_playing_in"]:
                await self.config.guild(guild).currently_auto_playing_in.set(
                    [notify_channel, player.channel.id]
                )
        else:
            if guild_data["currently_auto_playing_in"]:
                await self.config.guild(guild).currently_auto_playing_in.set([])

        if not (track or requester):
            return

        if notify:
            description = await self.get_track_description(track, self.local_folder_current_path)
            current_stream = self.rgetattr(track, "is_stream", None)
            current_length = self.rgetattr(track, "length", None)
            current_thumbnail = self.rgetattr(track, "thumbnail", None)

            notify_channel_id = player.fetch("notify_channel")
            notify_channel = self.bot.get_channel(notify_channel_id)
            if notify_channel and self._has_notify_perms(notify_channel):
                if player.fetch("notify_message") is not None:
                    with contextlib.suppress(discord.HTTPException):
                        await player.fetch("notify_message").delete()
                if not (description and notify_channel):
                    return
                if current_stream:
                    dur = "LIVE"
                else:
                    dur = self.format_time(current_length)

                thumb = None
                if guild_data["thumbnail"] and current_thumbnail:
                    thumb = current_thumbnail

                notify_message = await self.send_embed_msg(
                    notify_channel,
                    title=_("Now Playing"),
                    description=description,
                    footer=_("Track length: {length} | Requested by: {user}").format(
                        length=dur, user=requester
                    ),
                    thumbnail=thumb,
                )
                player.store("notify_message", notify_message)

        if status:
            player_check = await self.get_active_player_count()
            await self.update_bot_presence(*player_check)

        if await self.bot.cog_disabled_in_guild(self, guild):
            player = audio.get_player(guild.id)
            player.store("autoplay_notified", False)
            await player.stop()
            await player.disconnect()
            await self.config.guild_from_id(guild_id=guild.id).currently_auto_playing_in.set([])
            return

        track_identifier = track.track_identifier
        if self.playlist_api is not None:
            daily_cache = self._daily_playlist_cache.setdefault(
                guild.id, guild_data["daily_playlists"]
            )
            global_daily_playlists = self._daily_global_playlist_cache.setdefault(
                self.bot.user.id, global_data["daily_playlists"]
            )
            today = datetime.date.today()
            midnight = datetime.datetime.combine(today, datetime.datetime.min.time())
            today_id = int(time.mktime(today.timetuple()))
            track = self.track_to_json(track)
            if daily_cache:
                name = f"Daily playlist - {today}"
                playlist: Optional[Playlist]
                try:
                    playlist = await get_playlist(
                        playlist_api=self.playlist_api,
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
                        scope=PlaylistScope.GUILD.value,
                        author=self.bot.user.id,
                        playlist_id=today_id,
                        name=name,
                        playlist_url=None,
                        tracks=[track],
                        guild=guild,
                        playlist_api=self.playlist_api,
                    )
                    await playlist.save()
            if global_daily_playlists:
                global_name = f"Global Daily playlist - {today}"
                try:
                    playlist = await get_playlist(
                        playlist_number=today_id,
                        scope=PlaylistScope.GLOBAL.value,
                        bot=self.bot,
                        guild=guild,
                        author=self.bot.user,
                        playlist_api=self.playlist_api,
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
                        scope=PlaylistScope.GLOBAL.value,
                        author=self.bot.user.id,
                        playlist_id=today_id,
                        name=global_name,
                        playlist_url=None,
                        tracks=[track],
                        guild=guild,
                        playlist_api=self.playlist_api,
                    )
                    await playlist.save()
            too_old = midnight - datetime.timedelta(days=8)
            too_old_id = int(time.mktime(too_old.timetuple()))
            try:
                await delete_playlist(
                    scope=PlaylistScope.GUILD.value,
                    playlist_id=too_old_id,
                    guild=guild,
                    author=self.bot.user,
                    playlist_api=self.playlist_api,
                    bot=self.bot,
                )
            except Exception as err:
                debug_exc_log(log, err, "Failed to delete daily playlist ID: %d", too_old_id)
            try:
                await delete_playlist(
                    scope=PlaylistScope.GLOBAL.value,
                    playlist_id=too_old_id,
                    guild=guild,
                    author=self.bot.user,
                    playlist_api=self.playlist_api,
                    bot=self.bot,
                )
            except Exception as err:
                debug_exc_log(
                    log, err, "Failed to delete global daily playlist ID: %d", too_old_id
                )
        persist_cache = self._persist_queue_cache.setdefault(guild.id, guild_data["persist_queue"])
        if persist_cache:
            await self.api_interface.persistent_queue_api.played(
                guild_id=guild.id, track_id=track_identifier
            )

    @commands.Cog.listener()
    async def on_red_audio_queue_end(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member
    ):
        if not guild:
            return

        try:
            player = audio.get_player(guild.id)
        except NotConnectedToVoice:
            pass

        if player:
            guild_data = await self.config.guild(guild).all()
            autoplay = guild_data["auto_play"]
            notify = guild_data["notify"]
            disconnect = guild_data["disconnect"]
            status = await self.config.status()
            notify_channel_id = player.fetch("notify_channel")
            if player._ll_player.is_auto_playing or (
                autoplay
                and not player.queue
                and player.fetch("playing_song")
                and self.playlist_api
                and self.api_interface
            ):
                try:
                    await self.api_interface.autoplay(player, self.playlist_api)
                except DatabaseError:
                    notify_channel = self.bot.get_channel(notify_channel_id)
                    if notify_channel and self._has_notify_perms(notify_channel):
                        await self.send_embed_msg(
                            notify_channel, title=_("Couldn't get a valid track.")
                        )
                    return
                except TrackEnqueueError:
                    notify_channel = self.bot.get_channel(notify_channel_id)
                    if notify_channel and self._has_notify_perms(notify_channel):
                        await self.send_embed_msg(
                            notify_channel,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable to get a track from Lavalink at the moment, try again in a few "
                                "minutes."
                            ),
                        )
                    return

            if not autoplay:
                notify_channel = self.bot.get_channel(notify_channel_id)
                if notify_channel and notify and self._has_notify_perms(notify_channel):
                    await self.send_embed_msg(notify_channel, title=_("Queue ended."))
                if disconnect:
                    if guild_data["currently_auto_playing_in"]:
                        await self.config.guild(guild).currently_auto_playing_in.set([])
                    await player.disconnect()
                    self._ll_guild_updates.discard(guild.id)

            if status:
                player_check = await self.get_active_player_count()
                await self.update_bot_presence(*player_check)

        if self.playlist_api:
            await self.playlist_api.delete_scheduled()

    @commands.Cog.listener()
    async def on_red_audio_track_enqueue(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member
    ):
        if not (track and guild):
            return
        persist_cache = self._persist_queue_cache.setdefault(
            guild.id, await self.config.guild(guild).persist_queue()
        )
        if persist_cache:
            await self.api_interface.persistent_queue_api.enqueued(
                guild_id=guild.id, room_id=track.extras["vc"], track=track
            )

    @commands.Cog.listener()
    async def on_red_audio_track_end(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member, reason
    ):
        status = await self.config.status()

        try:
            player = audio._get_ll_player(guild)
        except NotConnectedToVoice:
            return

        if (not player.is_playing) and status:
            player_check = await self.get_active_player_count()
            await self.update_bot_presence(*player_check)

        if not (track and guild):
            return

        if self.playlist_api:
            await self.playlist_api.delete_scheduled()

    @commands.Cog.listener()
    async def on_red_audio_track_auto_play(
        self,
        guild: discord.Guild,
        track: lavalink.Track,
        requester: discord.Member,
        player: lavalink.Player,
    ):
        notify_channel = self.bot.get_channel(player.fetch("notify_channel"))
        has_perms = self._has_notify_perms(notify_channel)
        tries = 0
        while not player._is_playing:
            await asyncio.sleep(0.1)
            if tries > 1000:
                return
            tries += 1

        if notify_channel and has_perms and not player.fetch("autoplay_notified", False):
            if (
                len(player.manager.players) < 10
                or not player._last_resume
                and player._last_resume + datetime.timedelta(seconds=60)
                > datetime.datetime.now(tz=datetime.timezone.utc)
            ):
                await self.send_embed_msg(notify_channel, title=_("Auto Play started."))
            player.store("autoplay_notified", True)
