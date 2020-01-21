import asyncio
import contextlib
import datetime
import logging
import time
from typing import Optional

import discord
import lavalink

from redbot.core import commands

from ...apis.playlist_interface import Playlist, delete_playlist, get_playlist
from ...utils import PlaylistScope
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Events.audio")


class AudioEvents(MixinMeta, metaclass=CompositeMetaClass):
    @commands.Cog.listener()
    async def on_red_audio_track_start(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member
    ):
        if self.playlist_api is not None:
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
                track = self.track_to_json(track)
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
                        scope=scope,
                        author=self.bot.user.id,
                        playlist_id=today_id,
                        name=name,
                        playlist_url=None,
                        tracks=[track],
                        guild=guild,
                        playlist_api=self.playlist_api,
                    )
                    await playlist.save()

            with contextlib.suppress(Exception):
                too_old = midnight - datetime.timedelta(days=8)
                too_old_id = int(time.mktime(too_old.timetuple()))
                await delete_playlist(
                    bot=self.bot,
                    playlist_api=self.playlist_api,
                    scope=scope,
                    playlist_id=too_old_id,
                    guild=guild,
                    author=self.bot.user,
                )

    @commands.Cog.listener()
    async def on_red_audio_queue_end(
        self, guild: discord.Guild, track: lavalink.Track, requester: discord.Member
    ):
        if self.api_interface is not None and self.playlist_api is not None:
            await self.api_interface.local_cache_api.youtube.clean_up_old_entries()
            await asyncio.sleep(5)
            await self.playlist_api.delete_scheduled()
