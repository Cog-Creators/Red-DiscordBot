import asyncio
import contextlib
import datetime
import logging
from pathlib import Path
from typing import Dict

import discord
import lavalink
from discord.backoff import ExponentialBackoff
from discord.gateway import DiscordWebSocket

from redbot.core.i18n import Translator, set_contextual_locales_from_guild
from ...errors import DatabaseError, TrackEnqueueError
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Events.lavalink")
_ = Translator("Audio", Path(__file__))


class LavalinkEvents(MixinMeta, metaclass=CompositeMetaClass):
    async def lavalink_update_handler(
        self, player: lavalink.Player, event_type: lavalink.enums.PlayerState, extra
    ):
        self._last_ll_update = datetime.datetime.now(datetime.timezone.utc)
        self._ll_guild_updates.add(int(extra.get("guildId", 0)))

    async def lavalink_event_handler(
        self, player: lavalink.Player, event_type: lavalink.LavalinkEvents, extra
    ) -> None:
        current_track = player.current
        current_channel = player.channel
        guild = self.rgetattr(current_channel, "guild", None)
        if not (current_channel and guild):
            player.store("autoplay_notified", False)
            await player.stop()
            await player.disconnect()
            return
        if await self.bot.cog_disabled_in_guild(self, guild):
            await player.stop()
            await player.disconnect()
            if guild:
                await self.config.guild_from_id(guild_id=guild.id).currently_auto_playing_in.set(
                    []
                )
            return
        guild_id = self.rgetattr(guild, "id", None)
        if not guild:
            return
        guild_data = await self.config.guild(guild).all()
        disconnect = guild_data["disconnect"]

        if event_type == lavalink.LavalinkEvents.WEBSOCKET_CLOSED:
            deafen = guild_data["auto_deafen"]
            await self._websocket_closed_handler(
                guild=guild, player=player, extra=extra, deafen=deafen, disconnect=disconnect
            )
            return

        await set_contextual_locales_from_guild(self.bot, guild)
        current_requester = self.rgetattr(current_track, "requester", None)
        current_stream = self.rgetattr(current_track, "is_stream", None)
        current_length = self.rgetattr(current_track, "length", None)
        current_thumbnail = self.rgetattr(current_track, "thumbnail", None)
        current_extras = self.rgetattr(current_track, "extras", {})
        current_id = self.rgetattr(current_track, "_info", {}).get("identifier")

        repeat = guild_data["repeat"]
        notify = guild_data["notify"]
        autoplay = guild_data["auto_play"]
        description = await self.get_track_description(
            current_track, self.local_folder_current_path
        )
        status = await self.config.status()
        log.debug(f"Received a new lavalink event for {guild_id}: {event_type}: {extra}")
        prev_song: lavalink.Track = player.fetch("prev_song")
        await self.maybe_reset_error_counter(player)

        if event_type == lavalink.LavalinkEvents.TRACK_START:
            self.skip_votes[guild] = []
            playing_song = player.fetch("playing_song")
            requester = player.fetch("requester")
            player.store("prev_song", playing_song)
            player.store("prev_requester", requester)
            player.store("playing_song", current_track)
            player.store("requester", current_requester)
            self.bot.dispatch("red_audio_track_start", guild, current_track, current_requester)
            if guild_id and current_track:
                await self.api_interface.persistent_queue_api.played(
                    guild_id=guild_id, track_id=current_track.track_identifier
                )
            notify_channel = player.fetch("channel")
            if notify_channel:
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    [notify_channel, player.channel.id]
                )
            else:
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    []
                )
        if event_type == lavalink.LavalinkEvents.TRACK_END:
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch("red_audio_track_end", guild, prev_song, prev_requester)
        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            prev_requester = player.fetch("prev_requester")
            self.bot.dispatch("red_audio_queue_end", guild, prev_song, prev_requester)
            if guild_id:
                await self.api_interface.persistent_queue_api.drop(guild_id)
            if player.is_auto_playing or (
                autoplay
                and not player.queue
                and player.fetch("playing_song") is not None
                and self.playlist_api is not None
                and self.api_interface is not None
            ):
                notify_channel = player.fetch("channel")
                try:
                    await self.api_interface.autoplay(player, self.playlist_api)
                except DatabaseError:
                    notify_channel = self.bot.get_channel(notify_channel)
                    if notify_channel:
                        await self.send_embed_msg(
                            notify_channel, title=_("Couldn't get a valid track.")
                        )
                    return
                except TrackEnqueueError:
                    notify_channel = self.bot.get_channel(notify_channel)
                    if notify_channel:
                        await self.send_embed_msg(
                            notify_channel,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable to get a track from Lavalink at the moment, try again in a few "
                                "minutes."
                            ),
                        )
                    return
        if event_type == lavalink.LavalinkEvents.TRACK_START and notify:
            notify_channel = player.fetch("channel")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                if player.fetch("notify_message") is not None:
                    with contextlib.suppress(discord.HTTPException):
                        await player.fetch("notify_message").delete()
                if not description:
                    return
                if current_stream:
                    dur = "LIVE"
                else:
                    dur = self.format_time(current_length)

                thumb = None
                if await self.config.guild(guild).thumbnail() and current_thumbnail:
                    thumb = current_thumbnail

                notify_message = await self.send_embed_msg(
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
            player_check = await self.get_active_player_count()
            await self.update_bot_presence(*player_check)

        if event_type == lavalink.LavalinkEvents.TRACK_END and status:
            await asyncio.sleep(1)
            if not player.is_playing:
                player_check = await self.get_active_player_count()
                await self.update_bot_presence(*player_check)

        if event_type == lavalink.LavalinkEvents.QUEUE_END:
            if not autoplay:
                notify_channel = player.fetch("channel")
                if notify_channel and notify:
                    notify_channel = self.bot.get_channel(notify_channel)
                    await self.send_embed_msg(notify_channel, title=_("Queue ended."))
                if disconnect:
                    self.bot.dispatch("red_audio_audio_disconnect", guild)
                    await self.config.guild_from_id(
                        guild_id=guild_id
                    ).currently_auto_playing_in.set([])
                    await player.disconnect()
                    self._ll_guild_updates.discard(guild.id)
            if status:
                player_check = await self.get_active_player_count()
                await self.update_bot_presence(*player_check)

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
            guild_id = int(guild_id)
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
                player.store("autoplay_notified", False)
                if eq:
                    await self.config.custom("EQUALIZER", guild_id).eq_bands.set(eq.bands)
                await player.stop()
                await player.disconnect()
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    []
                )
                self._ll_guild_updates.discard(guild_id)
                self.bot.dispatch("red_audio_audio_disconnect", guild)
            if message_channel:
                message_channel = self.bot.get_channel(message_channel)
                if early_exit:
                    embed = discord.Embed(
                        colour=await self.bot.get_embed_color(message_channel),
                        title=_("Multiple Errors Detected"),
                        description=_(
                            "Closing the audio player "
                            "due to multiple errors being detected. "
                            "If this persists, please inform the bot owner "
                            "as the Audio cog may be temporally unavailable."
                        ),
                    )
                    await message_channel.send(embed=embed)
                    return
                else:
                    description = description or ""
                    if event_type == lavalink.LavalinkEvents.TRACK_STUCK:
                        embed = discord.Embed(
                            colour=await self.bot.get_embed_color(message_channel),
                            title=_("Track Stuck"),
                            description=_(
                                "Playback of the song has stopped due to an unexcepted error.\n{error}"
                            ).format(error=description),
                        )
                    else:
                        embed = discord.Embed(
                            title=_("Track Error"),
                            colour=await self.bot.get_embed_color(message_channel),
                            description="{}\n{}".format(extra.replace("\n", ""), description),
                        )
                        if current_id:
                            asyncio.create_task(
                                self.api_interface.global_cache_api.report_invalid(current_id)
                            )
                    await message_channel.send(embed=embed)
            await player.skip()

    async def _websocket_closed_handler(
        self,
        guild: discord.Guild,
        player: lavalink.Player,
        extra: Dict,
        deafen: bool,
        disconnect: bool,
    ) -> None:
        guild_id = guild.id
        node = player.node
        voice_ws: DiscordWebSocket = node.get_voice_ws(guild_id)
        code = extra.get("code")
        by_remote = extra.get("byRemote", "")
        reason = extra.get("reason", "").strip()
        if self._ws_resume[guild_id].is_set():
            log.debug(
                f"WS EVENT | Discarding WS Closed event for guild {guild_id} -> "
                f"Socket Closed {voice_ws.socket._closing or voice_ws.socket.closed}.  "
                f"Code: {code} -- Remote: {by_remote} -- {reason}"
            )
            return
        self._ws_resume[guild_id].set()
        if player.channel:
            current_perms = player.channel.permissions_for(player.channel.guild.me)
            has_perm = current_perms.speak and current_perms.connect
        else:
            has_perm = False
        if code in (4015, 4014, 4009, 4006):
            if player._con_delay:
                delay = player._con_delay.delay()
            else:
                player._con_delay = ExponentialBackoff(base=1)
                delay = player._con_delay.delay()
            channel_id = player.channel.id
            log.warning(
                "YOU CAN IGNORE THIS UNLESS IT'S CONSISTENTLY REPEATING FOR THE SAME GUILD - "
                f"Voice websocket closed for guild {guild_id} -> "
                f"Socket Closed {voice_ws.socket._closing or voice_ws.socket.closed}.  "
                f"Code: {code} -- Remote: {by_remote} -- {reason}")
            log.info(f"Reconnecting to channel {channel_id} in guild: {guild_id} | {delay:.2f}s'")
            await asyncio.sleep(delay)
            while voice_ws.socket._closing or voice_ws.socket.closed or not voice_ws.open:
                voice_ws = node.get_voice_ws(guild_id)
                await asyncio.sleep(0.1)

            if has_perm and player.current and player.is_playing:
                await player.connect(deafen=deafen)
                await player.resume(player.current, start=player.position)
                log.info(
                    "Voice websocket reconnected "
                    f"to channel {channel_id} in guild: {guild_id} | "
                    "Reason: Currently playing."
                )
            elif has_perm and player.paused and player.current:
                await player.connect(deafen=deafen)
                await player.pause(pause=True)
                log.info(
                    "Voice websocket reconnected "
                    f"to channel {channel_id} in guild: {guild_id} | "
                    "Reason: Currently Paused."
                )
            elif has_perm and (not disconnect) and (not player.is_playing):
                await player.connect(deafen=deafen)
                log.info(
                    "Voice websocket reconnected "
                    f"to channel {channel_id} in guild: {guild_id} | "
                    "Reason: Not playing, but auto disconnect disabled."
                )
                self._ll_guild_updates.discard(guild_id)
            elif not has_perm:
                self.bot.dispatch("red_audio_audio_disconnect", guild)
                log.info(
                    "Voice websocket disconnected "
                    f"from channel {channel_id} in guild: {guild_id} | "
                    "Reason: Missing permissions."
                )
                self._ll_guild_updates.discard(guild_id)
                player.store("autoplay_notified", False)
                await player.stop()
                await player.disconnect()
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    []
                )
            else:
                self.bot.dispatch("red_audio_audio_disconnect", guild)
                log.info(
                    "Voice websocket disconnected "
                    f"from channel {channel_id} in guild: {guild_id} | "
                    "Reason: Unknown."
                )
                self._ll_guild_updates.discard(guild_id)
                player.store("autoplay_notified", False)
                await player.stop()
                await player.disconnect()
                await self.config.guild_from_id(guild_id=guild_id).currently_auto_playing_in.set(
                    []
                )
        else:
            log.info(
                "WS EVENT - IGNORED (Healthy Socket) | "
                f"Voice websocket closed event for guild {guild_id} -> "
                f"Code: {code} -- Remote: {by_remote} -- {reason}"
            )
        self._ws_resume[guild_id].clear()
