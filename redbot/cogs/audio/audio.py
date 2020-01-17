import asyncio
import contextlib
import datetime
import heapq
import json
import logging
import os.path
import random
import re
import tarfile
import time
import traceback
from collections import Counter, namedtuple
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple, Union, cast, MutableMapping, Mapping

import aiohttp
import discord
import lavalink
import math
from discord.embeds import EmptyEmbed
from discord.utils import escape_markdown as escape
from fuzzywuzzy import process

from redbot.core import Config, bank, checks, commands
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import bold, box, humanize_number, inline, pagify
from redbot.core.utils.menus import (
    DEFAULT_CONTROLS,
    close_menu,
    menu,
    next_page,
    prev_page,
    start_adding_reactions,
)
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from .apis.interface import AudioAPIInterface
from .apis.playlist_interface import (
    get_all_playlist_for_migration23,
    get_playlist,
    Playlist,
    create_playlist,
    delete_playlist,
    get_all_playlist,
)
from .apis.utils import FakePlaylist
from .audio_dataclasses import Query, LocalPath, _PARTIALLY_SUPPORTED_MUSIC_EXT
from .audio_globals import update_audio_globals, get_playlist_api_wrapper
from .audio_logging import IS_DEBUG
from .converters import ComplexScopeParser, ScopeParser, get_lazy_converter, get_playlist_converter
from .equalizer import Equalizer
from .errors import (
    DatabaseError,
    LavalinkDownloadFailed,
    MissingGuild,
    QueryUnauthorized,
    SpotifyFetchError,
    TooManyMatches,
    TrackEnqueueError,
)
from .manager import ServerManager
from .utils import *


class Audio(commands.Cog):
    """Play audio through voice channels."""

    async def play_query(
        self,
        query: str,
        guild: discord.Guild,
        channel: discord.VoiceChannel,
        is_autoplay: bool = True,
    ):
        if not self._player_check(guild.me):
            try:
                if (
                    not channel.permissions_for(guild.me).connect
                    or not channel.permissions_for(guild.me).move_members
                    and userlimit(channel)
                ):
                    log.error(f"I don't have permission to connect to {channel} in {guild}.")

                await lavalink.connect(channel)
                player = lavalink.get_player(guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except IndexError:
                log.debug(
                    "Connection to Lavalink has not yet been established"
                    f" while trying to connect to to {channel} in {guild}."
                )
                return
        query = Query.process_input(query)
        restrict = await self.config.restrict()
        if restrict and match_url(query):
            valid_url = url_check(query)
            if not valid_url:
                raise QueryUnauthorized(f"{query} is not an allowed query.")
        elif not await is_allowed(guild, f"{query}", query_obj=query):
            raise QueryUnauthorized(f"{query} is not an allowed query.")

        player = lavalink.get_player(guild.id)
        player.store("channel", channel.id)
        player.store("guild", guild.id)
        await self._data_check(guild.me)

        ctx = namedtuple("Context", "message")
        (results, called_api) = await self.api_interface.fetch_track(ctx(guild), player, query)

        if not results.tracks:
            log.debug("Query returned no tracks.")
            return
        track = results.tracks[0]

        if not await is_allowed(
            guild, f"{track.title} {track.author} {track.uri} {str(query._raw)}"
        ):
            if IS_DEBUG:
                log.debug(f"Query is not allowed in {guild} ({guild.id})")
            return
        track.extras["autoplay"] = is_autoplay
        player.add(player.channel.guild.me, track)
        self.bot.dispatch(
            "red_audio_track_auto_play", player.channel.guild, track, player.channel.guild.me
        )
        if not player.current:
            await player.play()

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def audiostats(self, ctx: commands.Context):
        """Audio stats."""
        server_num = len(lavalink.active_players())
        total_num = len(lavalink.all_players())
        localtracks = await self.config.localpath()

        msg = ""
        for p in lavalink.all_players():
            connect_start = p.fetch("connect")
            connect_dur = dynamic_time(
                int((datetime.datetime.utcnow() - connect_start).total_seconds())
            )
            try:
                query = Query.process_input(p.current.uri)
                if query.is_local:
                    if p.current.title == "Unknown title":
                        current_title = localtracks.LocalPath(p.current.uri).to_string_user()
                        msg += "{} [`{}`]: **{}**\n".format(
                            p.channel.guild.name, connect_dur, current_title
                        )
                    else:
                        current_title = p.current.title
                        msg += "{} [`{}`]: **{} - {}**\n".format(
                            p.channel.guild.name, connect_dur, p.current.author, current_title
                        )
                else:
                    msg += "{} [`{}`]: **[{}]({})**\n".format(
                        p.channel.guild.name, connect_dur, p.current.title, p.current.uri
                    )
            except AttributeError:
                msg += "{} [`{}`]: **{}**\n".format(
                    p.channel.guild.name, connect_dur, _("Nothing playing.")
                )

        if total_num == 0:
            return await self._embed_msg(ctx, title=_("Not connected anywhere."))
        servers_embed = []
        pages = 1
        for page in pagify(msg, delims=["\n"], page_length=1500):
            em = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Playing in {num}/{total} servers:").format(
                    num=humanize_number(server_num), total=humanize_number(total_num)
                ),
                description=page,
            )
            em.set_footer(
                text="Page {}/{}".format(
                    humanize_number(pages), humanize_number((math.ceil(len(msg) / 1500)))
                )
            )
            pages += 1
            servers_embed.append(em)

        await menu(ctx, servers_embed, DEFAULT_CONTROLS)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def bump(self, ctx: commands.Context, index: int):
        """Bump a track number to the top of the queue."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )

        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Bump Track"),
                description=_("You must be in the voice channel to bump a track."),
            )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Bump Track"),
                    description=_("You need the DJ role to bump tracks."),
                )
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Bump Track"),
                description=_("Song number must be greater than 1 and within the queue limit."),
            )

        bump_index = index - 1
        bump_song = player.queue[bump_index]
        bump_song.extras["bumped"] = True
        player.queue.insert(0, bump_song)
        removed = player.queue.pop(index)
        description = get_track_description(removed)
        await self._embed_msg(
            ctx, title=_("Moved track to the top of the queue."), description=description
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def disconnect(self, ctx: commands.Context):
        """Disconnect from the voice channel."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        else:
            dj_enabled = self._dj_status_cache.setdefault(
                ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
            )
            player = lavalink.get_player(ctx.guild.id)

            if dj_enabled:
                if not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable to disconnect"),
                        description=_("You need the DJ role to disconnect."),
                    )
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                return await self._embed_msg(
                    ctx, title=_("There are other people listening to music.")
                )
            else:
                await self._embed_msg(ctx, title=_("Disconnecting..."))
                self.bot.dispatch("red_audio_audio_disconnect", ctx.guild)
                self._play_lock(ctx, False)
                eq = player.fetch("eq")
                player.queue = []
                player.store("playing_song", None)
                if eq:
                    await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
                await player.stop()
                await player.disconnect()

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def now(self, ctx: commands.Context):
        """Now playing."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        expected = ("⏮", "⏹", "⏯", "⏭")
        emoji = {"prev": "⏮", "stop": "⏹", "pause": "⏯", "next": "⏭"}
        player = lavalink.get_player(ctx.guild.id)
        if player.current:
            arrow = await draw_time(ctx)
            pos = lavalink.utils.format_time(player.position)
            if player.current.is_stream:
                dur = "LIVE"
            else:
                dur = lavalink.utils.format_time(player.current.length)
            song = get_track_description(player.current)
            song += _("\n Requested by: **{track.requester}**")
            song += "\n\n{arrow}`{pos}`/`{dur}`"
            song = song.format(track=player.current, arrow=arrow, pos=pos, dur=dur)
        else:
            song = _("Nothing.")

        if player.fetch("np_message") is not None:
            with contextlib.suppress(discord.HTTPException):
                await player.fetch("np_message").delete()

        embed = discord.Embed(title=_("Now Playing"), description=song)
        if await self.config.guild(ctx.guild).thumbnail() and player.current:
            if player.current.thumbnail:
                embed.set_thumbnail(url=player.current.thumbnail)

        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        autoplay = await self.config.guild(ctx.guild).auto_play()
        text = ""
        text += (
            _("Auto-Play")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if autoplay else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Shuffle")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if shuffle else "\N{CROSS MARK}")
        )
        text += (
            (" | " if text else "")
            + _("Repeat")
            + ": "
            + ("\N{WHITE HEAVY CHECK MARK}" if repeat else "\N{CROSS MARK}")
        )

        message = await self._embed_msg(ctx, embed=embed, footer=text)

        player.store("np_message", message)

        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if dj_enabled or vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                return

        if not player.queue:
            expected = ("⏹", "⏯")
        if player.current:
            task = start_adding_reactions(message, expected[:4], ctx.bot.loop)
        else:
            task = None

        try:
            (r, u) = await self.bot.wait_for(
                "reaction_add",
                check=ReactionPredicate.with_emojis(expected, message, ctx.author),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            return await self._clear_react(message, emoji)
        else:
            if task is not None:
                task.cancel()
        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.emoji]
        if react == "prev":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.prev)
        elif react == "stop":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.stop)
        elif react == "pause":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.pause)
        elif react == "next":
            await self._clear_react(message, emoji)
            await ctx.invoke(self.skip)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def pause(self, ctx: commands.Context):
        """Pause or resume a playing track."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Manage Tracks"),
                description=_("You must be in the voice channel to pause or resume."),
            )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Manage Tracks"),
                    description=_("You need the DJ role to pause or resume tracks."),
                )

        if not player.current:
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        description = get_track_description(player.current)

        if player.current and not player.paused:
            await player.pause()
            return await self._embed_msg(ctx, title=_("Track Paused"), description=description)
        if player.current and player.paused:
            await player.pause(False)
            return await self._embed_msg(ctx, title=_("Track Resumed"), description=description)

        await self._embed_msg(ctx, title=_("Nothing playing."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def percent(self, ctx: commands.Context):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        queue_tracks = player.queue
        requesters = {"total": 0, "users": {}}

        async def _usercount(req_username):
            if req_username in requesters["users"]:
                requesters["users"][req_username]["songcount"] += 1
                requesters["total"] += 1
            else:
                requesters["users"][req_username] = {}
                requesters["users"][req_username]["songcount"] = 1
                requesters["total"] += 1

        for track in queue_tracks:
            req_username = "{}#{}".format(track.requester.name, track.requester.discriminator)
            await _usercount(req_username)
            await asyncio.sleep(0)

        try:
            req_username = "{}#{}".format(
                player.current.requester.name, player.current.requester.discriminator
            )
            await _usercount(req_username)
        except AttributeError:
            return await self._embed_msg(ctx, title=_("There's  nothing in the queue."))

        for req_username in requesters["users"]:
            percentage = float(requesters["users"][req_username]["songcount"]) / float(
                requesters["total"]
            )
            requesters["users"][req_username]["percent"] = round(percentage * 100, 1)
            await asyncio.sleep(0)

        top_queue_users = heapq.nlargest(
            20,
            [
                (x, requesters["users"][x][y])
                for x in requesters["users"]
                for y in requesters["users"][x]
                if y == "percent"
            ],
            key=lambda x: x[1],
        )
        queue_user = ["{}: {:g}%".format(x[0], x[1]) for x in top_queue_users]
        queue_user_list = "\n".join(queue_user)
        await self._embed_msg(
            ctx, title=_("Queued and playing tracks:"), description=queue_user_list
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def play(self, ctx: commands.Context, *, query: str):
        """Play a URL or search for a track."""
        query = Query.process_input(query)
        guild_data = await self.config.guild(ctx.guild).all()
        restrict = await self.config.restrict()
        if restrict and match_url(query):
            valid_url = url_check(query)
            if not valid_url:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("That URL is not allowed."),
                )
        elif not await is_allowed(ctx.guild, f"{query}", query_obj=query):
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("That track is not allowed.")
            )
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, title=msg, description=desc)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("I don't have permission to connect to your channel."),
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        if guild_data["dj_enabled"]:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("You need the DJ role to queue tracks."),
                )
        player = lavalink.get_player(ctx.guild.id)

        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the play command."),
            )
        if not query.valid:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("No tracks found for `{query}`.").format(
                    query=query.to_string_user()
                ),
            )
        if len(player.queue) >= 10000:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )

        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        if query.is_spotify:
            return await self._get_spotify_tracks(ctx, query)
        try:
            await self._enqueue_tracks(ctx, query)
        except QueryUnauthorized as err:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=err.message
            )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def bumpplay(
        self, ctx: commands.Context, play_now: Optional[bool] = False, *, query: str
    ):
        """Force play a URL or search for a track."""
        query = Query.process_input(query)
        if not query.single_track:
            return await self._embed_msg(
                ctx,
                title=_("Unable to bump track"),
                description=_("Only single tracks work with bump play."),
            )
        guild_data = await self.config.guild(ctx.guild).all()
        restrict = await self.config.restrict()
        if restrict and match_url(query):
            valid_url = url_check(query)
            if not valid_url:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("That URL is not allowed."),
                )
        elif not await is_allowed(ctx.guild, f"{query}", query_obj=query):
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("That track is not allowed.")
            )
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, title=msg, description=desc)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("I don't have permission to connect to your channel."),
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        if guild_data["dj_enabled"]:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("You need the DJ role to queue tracks."),
                )
        player = lavalink.get_player(ctx.guild.id)

        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the play command."),
            )
        if not query.valid:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("No tracks found for `{query}`.").format(
                    query=query.to_string_user()
                ),
            )
        if len(player.queue) >= 10000:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )

        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        try:
            if query.is_spotify:
                tracks = await self._get_spotify_tracks(ctx, query)
            else:
                tracks = await self._enqueue_tracks(ctx, query, enqueue=False)
        except QueryUnauthorized as err:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=err.message
            )
        if isinstance(tracks, discord.Message):
            return
        elif not tracks:
            self._play_lock(ctx, False)
            title = _("Unable To Play Tracks")
            desc = _("No tracks found for `{query}`.").format(query=query.to_string_user())
            embed = discord.Embed(title=title, description=desc)
            if await self.config.use_external_lavalink() and query.is_local:
                embed.description = _(
                    "Local tracks will not work "
                    "if the `Lavalink.jar` cannot see the track.\n"
                    "This may be due to permissions or because Lavalink.jar is being run "
                    "in a different machine than the local tracks."
                )
            elif query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                title = _("Track is not playable.")
                embed = discord.Embed(title=title)
                embed.description = _(
                    "**{suffix}** is not a fully supported format and some " "tracks may not play."
                ).format(suffix=query.suffix)
            return await self._embed_msg(ctx, embed=embed)
        elif isinstance(tracks, discord.Message):
            return
        queue_dur = await queue_duration(ctx)
        lavalink.utils.format_time(queue_dur)
        index = query.track_index
        seek = 0
        if query.start_time:
            seek = query.start_time
        single_track = (
            tracks
            if isinstance(tracks, lavalink.rest_api.Track)
            else tracks[index]
            if index
            else tracks[0]
        )
        if seek and seek > 0:
            single_track.start_timestamp = seek * 1000
        if not await is_allowed(
            ctx.guild,
            (
                f"{single_track.title} {single_track.author} {single_track.uri} "
                f"{str(Query.process_input(single_track))}"
            ),
        ):
            if IS_DEBUG:
                log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
            self._play_lock(ctx, False)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("This track is not allowed in this server."),
            )
        elif guild_data["maxlength"] > 0:
            if track_limit(single_track, guild_data["maxlength"]):
                single_track.requester = ctx.author
                player.queue.insert(0, single_track)
                player.maybe_shuffle()
                self.bot.dispatch(
                    "red_audio_track_enqueue", player.channel.guild, single_track, ctx.author
                )
            else:
                self._play_lock(ctx, False)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Track exceeds maximum length."),
                )

        else:
            single_track.requester = ctx.author
            single_track.extras["bumped"] = True
            player.queue.insert(0, single_track)
            player.maybe_shuffle()
            self.bot.dispatch(
                "red_audio_track_enqueue", player.channel.guild, single_track, ctx.author
            )
        description = get_track_description(single_track)
        footer = None
        if not play_now and not guild_data["shuffle"] and queue_dur > 0:
            footer = _("{time} until track playback: #1 in queue").format(
                time=lavalink.utils.format_time(queue_dur)
            )
        await self._embed_msg(
            ctx, title=_("Track Enqueued"), description=description, footer=footer
        )

        if not player.current:
            await player.play()
        elif play_now:
            await player.skip()

        self._play_lock(ctx, False)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def genre(self, ctx: commands.Context):
        """Pick a Spotify playlist from a list of categories to start playing."""

        async def _category_search_menu(
            ctx: commands.Context,
            pages: list,
            controls: MutableMapping,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                output = await self._genre_search_button_action(ctx, category_list, emoji, page)
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return output

        async def _playlist_search_menu(
            ctx: commands.Context,
            pages: list,
            controls: MutableMapping,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                output = await self._genre_search_button_action(
                    ctx, playlists_list, emoji, page, playlist=True
                )
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return output

        category_search_controls = {
            "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}": _category_search_menu,
            "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}": _category_search_menu,
            "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}": _category_search_menu,
            "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}": _category_search_menu,
            "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}": _category_search_menu,
            "\N{LEFTWARDS BLACK ARROW}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}": next_page,
        }
        playlist_search_controls = {
            "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{LEFTWARDS BLACK ARROW}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}": next_page,
        }

        api_data = await self._check_api_tokens()
        if any(
            [
                not api_data["spotify_client_id"],
                not api_data["spotify_client_secret"],
                not api_data["youtube_api"],
            ]
        ):
            return await self._embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(
                    "The owner needs to set the Spotify client ID, Spotify client secret, "
                    "and YouTube API key before Spotify URLs or codes can be used. "
                    "\nSee `{prefix}audioset youtubeapi` and `{prefix}audioset spotifyapi` "
                    "for instructions."
                ).format(prefix=ctx.prefix),
            )
        guild_data = await self.config.guild(ctx.guild).all()
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, title=msg, description=desc)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("I don't have permission to connect to your channel."),
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        if guild_data["dj_enabled"]:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("You need the DJ role to queue tracks."),
                )
        player = lavalink.get_player(ctx.guild.id)

        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the genre command."),
            )
        try:
            category_list = await self.api_interface.spotify_api.get_categories()
        except SpotifyFetchError as error:
            return await self._embed_msg(
                ctx,
                title=_("No categories found"),
                description=_(error.message).format(prefix=ctx.prefix),
            )
        if not category_list:
            return await self._embed_msg(ctx, title=_("No categories found, try again later."))
        len_folder_pages = math.ceil(len(category_list) / 5)
        category_search_page_list = []
        for page_num in range(1, len_folder_pages + 1):
            embed = await self._build_genre_search_page(
                ctx, category_list, page_num, _("Categories")
            )
            category_search_page_list.append(embed)
            await asyncio.sleep(0)
        cat_menu_output = await menu(ctx, category_search_page_list, category_search_controls)
        if not cat_menu_output:
            return await self._embed_msg(ctx, title=_("No categories selected, try again later."))
        category_name, category_pick = cat_menu_output
        playlists_list = await self.api_interface.spotify_api.get_playlist_from_category(
            category_pick
        )
        if not playlists_list:
            return await self._embed_msg(ctx, title=_("No categories found, try again later."))
        len_folder_pages = math.ceil(len(playlists_list) / 5)
        playlists_search_page_list = []
        for page_num in range(1, len_folder_pages + 1):
            embed = await self._build_genre_search_page(
                ctx,
                playlists_list,
                page_num,
                _("Playlists for {friendly_name}").format(friendly_name=category_name),
                playlist=True,
            )
            playlists_search_page_list.append(embed)
            await asyncio.sleep(0)
        playlists_pick = await menu(ctx, playlists_search_page_list, playlist_search_controls)
        query = Query.process_input(playlists_pick)
        if not query.valid:
            return await self._embed_msg(ctx, title=_("No tracks to play."))
        if len(player.queue) >= 10000:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        if query.is_spotify:
            return await self._get_spotify_tracks(ctx, query)
        return await self._embed_msg(
            ctx, title=_("Couldn't find tracks for the selected playlist.")
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def autoplay(self, ctx: commands.Context):
        """Starts auto play."""
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, title=msg, description=desc)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("I don't have permission to connect to your channel."),
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        guild_data = await self.config.guild(ctx.guild).all()
        if guild_data["dj_enabled"]:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("You need the DJ role to queue tracks."),
                )
        player = lavalink.get_player(ctx.guild.id)

        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the autoplay command."),
            )
        if len(player.queue) >= 10000:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        try:
            await self.api_interface.autoplay(player)
        except DatabaseError:
            notify_channel = player.fetch("channel")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                await self._embed_msg(notify_channel, title=_("Couldn't get a valid track."))
            return

        if not guild_data["auto_play"]:
            await ctx.invoke(self._autoplay_toggle)
        if not guild_data["notify"] and (
            (player.current and not player.current.extras.get("autoplay")) or not player.current
        ):
            await self._embed_msg(ctx, title=_("Auto play started."))
        elif player.current:
            await self._embed_msg(ctx, title=_("Adding a track to queue."))

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def prev(self, ctx: commands.Context):
        """Skip to the start of the previously played track."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        is_alone = await self._is_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        player = lavalink.get_player(ctx.guild.id)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Skip Tracks"),
                description=_("You must be in the voice channel to skip the track."),
            )
        if vote_enabled or vote_enabled and dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Skip Tracks"),
                    description=_("There are other people listening - vote to skip instead."),
                )
        if dj_enabled and not vote_enabled:
            if not (can_skip or is_requester) and not is_alone:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Skip Tracks"),
                    description=_(
                        "You need the DJ role or be the track requester "
                        "to enqueue the previous song tracks."
                    ),
                )

        if player.fetch("prev_song") is None:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("No previous track.")
            )
        else:
            track = player.fetch("prev_song")
            player.add(player.fetch("prev_requester"), track)
            self.bot.dispatch("red_audio_track_enqueue", player.channel.guild, track, ctx.author)
            queue_len = len(player.queue)
            bump_song = player.queue[-1]
            player.queue.insert(0, bump_song)
            player.queue.pop(queue_len)
            await player.skip()
            description = get_track_description(player.current)
            embed = discord.Embed(title=_("Replaying Track"), description=description)
            await self._embed_msg(ctx, embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def repeat(self, ctx: commands.Context):
        """Toggle repeat."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._has_dj_role(
                ctx, ctx.author
            ):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Toggle Repeat"),
                    description=_("You need the DJ role to toggle repeat."),
                )
        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Toggle Repeat"),
                    description=_("You must be in the voice channel to toggle repeat."),
                )

        autoplay = await self.config.guild(ctx.guild).auto_play()
        repeat = await self.config.guild(ctx.guild).repeat()
        msg = ""
        msg += _("Repeat tracks: {true_or_false}.").format(
            true_or_false=_("Enabled") if not repeat else _("Disabled")
        )
        await self.config.guild(ctx.guild).repeat.set(not repeat)
        if repeat is not True and autoplay is True:
            msg += _("\nAuto-play has been disabled.")
            await self.config.guild(ctx.guild).auto_play.set(False)

        embed = discord.Embed(title=_("Setting Changed"), description=msg)
        await self._embed_msg(ctx, embed=embed)
        if self._player_check(ctx):
            await self._data_check(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def remove(self, ctx: commands.Context, index: int):
        """Remove a specific track number from the queue."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if not player.queue:
            return await self._embed_msg(ctx, title=_("Nothing queued."))
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Modify Queue"),
                    description=_("You need the DJ role to remove tracks."),
                )
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Modify Queue"),
                description=_("You must be in the voice channel to manage the queue."),
            )
        if index > len(player.queue) or index < 1:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Modify Queue"),
                description=_("Song number must be greater than 1 and within the queue limit."),
            )
        index -= 1
        removed = player.queue.pop(index)
        removed_title = get_track_description(removed)
        await self._embed_msg(
            ctx,
            title=_("Removed track from queue"),
            description=_("Removed {track} from the queue.").format(track=removed_title),
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def search(self, ctx: commands.Context, *, query: str):
        """Pick a track with a search.

        Use `[p]search list <search term>` to queue all tracks found on YouTube. `[p]search sc
        <search term>` will search SoundCloud instead of YouTube.
        """

        async def _search_menu(
            ctx: commands.Context,
            pages: list,
            controls: MutableMapping,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                await self._search_button_action(ctx, tracks, emoji, page)
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return None

        search_controls = {
            "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}": _search_menu,
            "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}": _search_menu,
            "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}": _search_menu,
            "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}": _search_menu,
            "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}": _search_menu,
            "\N{LEFTWARDS BLACK ARROW}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}": next_page,
        }

        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, title=msg, description=desc)
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Search For Tracks"),
                        description=_("I don't have permission to connect to your channel."),
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Search For Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Search For Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        player = lavalink.get_player(ctx.guild.id)
        guild_data = await self.config.guild(ctx.guild).all()
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Search For Tracks"),
                description=_("You must be in the voice channel to enqueue tracks."),
            )
        await self._eq_check(ctx, player)
        await self._data_check(ctx)

        before_queue_length = len(player.queue)

        if not isinstance(query, list):
            query = Query.process_input(query)
            restrict = await self.config.restrict()
            if restrict and match_url(query):
                valid_url = url_check(query)
                if not valid_url:
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("That URL is not allowed."),
                    )
            if not await is_allowed(ctx.guild, f"{query}", query_obj=query):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("That track is not allowed."),
                )
            if query.invoked_from == "search list" or query.invoked_from == "local folder":
                if query.invoked_from == "search list" and not query.is_local:
                    try:
                        result, called_api = await self.api_interface.fetch_track(
                            ctx, player, query
                        )
                    except TrackEnqueueError:
                        self._play_lock(ctx, False)
                        return await self._embed_msg(
                            ctx,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable get a track from Lavalink at the moment, try again in a "
                                "few "
                                "minutes."
                            ),
                        )

                    tracks = result.tracks
                else:
                    try:
                        tracks = await self._folder_tracks(ctx, player, query)
                    except TrackEnqueueError:
                        self._play_lock(ctx, False)
                        return await self._embed_msg(
                            ctx,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable get a track from Lavalink at the moment, try again in a "
                                "few "
                                "minutes."
                            ),
                        )
                if not tracks:
                    embed = discord.Embed(title=_("Nothing found."))
                    if await self.config.use_external_lavalink() and query.is_local:
                        embed.description = _(
                            "Local tracks will not work "
                            "if the `Lavalink.jar` cannot see the track.\n"
                            "This may be due to permissions or because Lavalink.jar is being run "
                            "in a different machine than the local tracks."
                        )
                    elif query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                        embed = discord.Embed(title=_("Track is not playable."))
                        embed.description = _(
                            "**{suffix}** is not a fully supported format and some "
                            "tracks may not play."
                        ).format(suffix=query.suffix)
                    return await self._embed_msg(ctx, embed=embed)
                queue_dur = await queue_duration(ctx)
                queue_total_duration = lavalink.utils.format_time(queue_dur)
                if guild_data["dj_enabled"]:
                    if not await self._can_instaskip(ctx, ctx.author):
                        return await self._embed_msg(
                            ctx,
                            title=_("Unable To Play Tracks"),
                            description=_("You need the DJ role to queue tracks."),
                        )
                track_len = 0
                empty_queue = not player.queue
                for track in tracks:
                    if len(player.queue) >= 10000:
                        continue
                    if not await is_allowed(
                        ctx.guild,
                        (
                            f"{track.title} {track.author} {track.uri} "
                            f"{str(Query.process_input(track))}"
                        ),
                    ):
                        if IS_DEBUG:
                            log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
                        continue
                    elif guild_data["maxlength"] > 0:
                        if track_limit(track, guild_data["maxlength"]):
                            track_len += 1
                            player.add(ctx.author, track)
                            self.bot.dispatch(
                                "red_audio_track_enqueue", player.channel.guild, track, ctx.author
                            )
                    else:
                        track_len += 1
                        player.add(ctx.author, track)
                        self.bot.dispatch(
                            "red_audio_track_enqueue", player.channel.guild, track, ctx.author
                        )
                    if not player.current:
                        await player.play()
                    await asyncio.sleep(0)
                player.maybe_shuffle(0 if empty_queue else 1)
                if len(tracks) > track_len:
                    maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                        bad_tracks=(len(tracks) - track_len)
                    )
                else:
                    maxlength_msg = ""
                songembed = discord.Embed(
                    title=_("Queued {num} track(s).{maxlength_msg}").format(
                        num=track_len, maxlength_msg=maxlength_msg
                    )
                )
                if not guild_data["shuffle"] and queue_dur > 0:
                    songembed.set_footer(
                        text=_(
                            "{time} until start of search playback: starts at #{position} in queue"
                        ).format(time=queue_total_duration, position=before_queue_length + 1)
                    )
                return await self._embed_msg(ctx, embed=songembed)
            elif query.is_local and query.single_track:
                tracks = await self._folder_list(ctx, query)
            elif query.is_local and query.is_album:
                if ctx.invoked_with == "folder":
                    return await self._local_play_all(ctx, query, from_search=True)
                else:
                    tracks = await self._folder_list(ctx, query)
            else:
                try:
                    result, called_api = await self.api_interface.fetch_track(ctx, player, query)
                except TrackEnqueueError:
                    self._play_lock(ctx, False)
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable to Get Track"),
                        description=_(
                            "I'm unable get a track from Lavalink at the moment,"
                            "try again in a few minutes."
                        ),
                    )
                tracks = result.tracks
            if not tracks:
                embed = discord.Embed(title=_("Nothing found."))
                if await self.config.use_external_lavalink() and query.is_local:
                    embed.description = _(
                        "Local tracks will not work "
                        "if the `Lavalink.jar` cannot see the track.\n"
                        "This may be due to permissions or because Lavalink.jar is being run "
                        "in a different machine than the local tracks."
                    )
                elif query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                    embed = discord.Embed(title=_("Track is not playable."))
                    embed.description = _(
                        "**{suffix}** is not a fully supported format and some "
                        "tracks may not play."
                    ).format(suffix=query.suffix)
                return await self._embed_msg(ctx, embed=embed)
        else:
            tracks = query

        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )

        len_search_pages = math.ceil(len(tracks) / 5)
        search_page_list = []
        for page_num in range(1, len_search_pages + 1):
            embed = await self._build_search_page(ctx, tracks, page_num)
            search_page_list.append(embed)
            await asyncio.sleep(0)

        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            return await menu(ctx, search_page_list, DEFAULT_CONTROLS)

        await menu(ctx, search_page_list, search_controls)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def seek(self, ctx: commands.Context, seconds: Union[int, str]):
        """Seek ahead or behind on a track by seconds or a to a specific time.

        Accepts seconds or a value formatted like 00:00:00 (`hh:mm:ss`) or 00:00 (`mm:ss`).
        """
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        is_alone = await self._is_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)

        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Seek Tracks"),
                description=_("You must be in the voice channel to use seek."),
            )

        if vote_enabled and not can_skip and not is_alone:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Seek Tracks"),
                description=_("There are other people listening - vote to skip instead."),
            )

        if dj_enabled and not (can_skip or is_requester) and not is_alone:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Seek Tracks"),
                description=_("You need the DJ role or be the track requester to use seek."),
            )

        if player.current:
            if player.current.is_stream:
                return await self._embed_msg(
                    ctx, title=_("Unable To Seek Tracks"), description=_("Can't seek on a stream.")
                )
            else:
                try:
                    int(seconds)
                    abs_position = False
                except ValueError:
                    abs_position = True
                    seconds = time_convert(seconds)
                if seconds == 0:
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Seek Tracks"),
                        description=_("Invalid input for the time to seek."),
                    )
                if not abs_position:
                    time_sec = int(seconds) * 1000
                    seek = player.position + time_sec
                    if seek <= 0:
                        await self._embed_msg(
                            ctx,
                            title=_("Moved {num_seconds}s to 00:00:00").format(
                                num_seconds=seconds
                            ),
                        )
                    else:
                        await self._embed_msg(
                            ctx,
                            title=_("Moved {num_seconds}s to {time}").format(
                                num_seconds=seconds, time=lavalink.utils.format_time(seek)
                            ),
                        )
                    await player.seek(seek)
                else:
                    await self._embed_msg(
                        ctx,
                        title=_("Moved to {time}").format(
                            time=lavalink.utils.format_time(seconds * 1000)
                        ),
                    )
                    await player.seek(seconds * 1000)
        else:
            await self._embed_msg(ctx, title=_("Nothing playing."))

    @commands.group(autohelp=False)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def shuffle(self, ctx: commands.Context):
        """Toggle shuffle."""
        if ctx.invoked_subcommand is None:
            dj_enabled = self._dj_status_cache.setdefault(
                ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
            )
            if dj_enabled:
                if not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Toggle Shuffle"),
                        description=_("You need the DJ role to toggle shuffle."),
                    )
            if self._player_check(ctx):
                await self._data_check(ctx)
                player = lavalink.get_player(ctx.guild.id)
                if (
                    not ctx.author.voice or ctx.author.voice.channel != player.channel
                ) and not await self._can_instaskip(ctx, ctx.author):
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Toggle Shuffle"),
                        description=_("You must be in the voice channel to toggle shuffle."),
                    )

            shuffle = await self.config.guild(ctx.guild).shuffle()
            await self.config.guild(ctx.guild).shuffle.set(not shuffle)
            await self._embed_msg(
                ctx,
                title=_("Setting Changed"),
                description=_("Shuffle tracks: {true_or_false}.").format(
                    true_or_false=_("Enabled") if not shuffle else _("Disabled")
                ),
            )
            if self._player_check(ctx):
                await self._data_check(ctx)

    @shuffle.command(name="bumped")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def _shuffle_bumpped(self, ctx: commands.Context):
        """Toggle bumped track shuffle.

        Set this to disabled if you wish to avoid bumped songs being shuffled. This takes priority
        over `[p]shuffle`.
        """
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Toggle Shuffle"),
                    description=_("You need the DJ role to toggle shuffle."),
                )
        if self._player_check(ctx):
            await self._data_check(ctx)
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Toggle Shuffle"),
                    description=_("You must be in the voice channel to toggle shuffle."),
                )

        bumped = await self.config.guild(ctx.guild).shuffle_bumped()
        await self.config.guild(ctx.guild).shuffle_bumped.set(not bumped)
        await self._embed_msg(
            ctx,
            title=_("Setting Changed"),
            description=_("Shuffle bumped tracks: {true_or_false}.").format(
                true_or_false=_("Enabled") if not bumped else _("Disabled")
            ),
        )
        if self._player_check(ctx):
            await self._data_check(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def sing(self, ctx: commands.Context):
        """Make Red sing one of her songs."""
        ids = (
            "zGTkAVsrfg8",
            "cGMWL8cOeAU",
            "vFrjMq4aL-g",
            "WROI5WYBU_A",
            "41tIUr_ex3g",
            "f9O2Rjn1azc",
        )
        url = f"https://www.youtube.com/watch?v={random.choice(ids)}"
        await ctx.invoke(self.play, query=url)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def skip(self, ctx: commands.Context, skip_to_track: int = None):
        """Skip to the next track, or to a given track number."""
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Skip Tracks"),
                description=_("You must be in the voice channel to skip the music."),
            )
        if not player.current:
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        is_alone = await self._is_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if dj_enabled and not vote_enabled:
            if not (can_skip or is_requester) and not is_alone:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Skip Tracks"),
                    description=_(
                        "You need the DJ role or be the track requester to skip tracks."
                    ),
                )
            if (
                is_requester
                and not can_skip
                and isinstance(skip_to_track, int)
                and skip_to_track > 1
            ):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Skip Tracks"),
                    description=_("You can only skip the current track."),
                )

        if vote_enabled:
            if not can_skip:
                if skip_to_track is not None:
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Skip Tracks"),
                        description=_(
                            "Can't skip to a specific track in vote mode without the DJ role."
                        ),
                    )
                if ctx.author.id in self.skip_votes[ctx.message.guild]:
                    self.skip_votes[ctx.message.guild].remove(ctx.author.id)
                    reply = _("I removed your vote to skip.")
                else:
                    self.skip_votes[ctx.message.guild].append(ctx.author.id)
                    reply = _("You voted to skip.")

                num_votes = len(self.skip_votes[ctx.message.guild])
                vote_mods = []
                for member in player.channel.members:
                    can_skip = await self._can_instaskip(ctx, member)
                    if can_skip:
                        vote_mods.append(member)
                num_members = len(player.channel.members) - len(vote_mods)
                vote = int(100 * num_votes / num_members)
                percent = await self.config.guild(ctx.guild).vote_percent()
                if vote >= percent:
                    self.skip_votes[ctx.message.guild] = []
                    await self._embed_msg(ctx, title=_("Vote threshold met."))
                    return await self._skip_action(ctx)
                else:
                    reply += _(
                        " Votes: {num_votes}/{num_members}"
                        " ({cur_percent}% out of {required_percent}% needed)"
                    ).format(
                        num_votes=humanize_number(num_votes),
                        num_members=humanize_number(num_members),
                        cur_percent=vote,
                        required_percent=percent,
                    )
                    return await self._embed_msg(ctx, title=reply)
            else:
                return await self._skip_action(ctx, skip_to_track)
        else:
            return await self._skip_action(ctx, skip_to_track)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def stop(self, ctx: commands.Context):
        """Stop playback and clear the queue."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self._embed_msg(
                ctx,
                title=_("Unable To Stop Player"),
                description=_("You must be in the voice channel to stop the music."),
            )
        if vote_enabled or vote_enabled and dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Stop Player"),
                    description=_("There are other people listening - vote to skip instead."),
                )
        if dj_enabled and not vote_enabled:
            if not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Stop Player"),
                    description=_("You need the DJ role to stop the music."),
                )
        if (
            player.is_playing
            or (not player.is_playing and player.paused)
            or player.queue
            or getattr(player.current, "extras", {}).get("autoplay")
        ):
            eq = player.fetch("eq")
            if eq:
                await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
            player.queue = []
            player.store("playing_song", None)
            player.store("prev_requester", None)
            player.store("prev_song", None)
            player.store("requester", None)
            await player.stop()
            await self._embed_msg(ctx, title=_("Stopping..."))

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.bot_has_permissions(embed_links=True)
    async def summon(self, ctx: commands.Context):
        """Summon the bot to a voice channel."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
        is_alone = await self._is_alone(ctx)
        is_requester = await self.is_requester(ctx, ctx.author)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if vote_enabled or (vote_enabled and dj_enabled):
            if not can_skip and not is_alone:
                ctx.command.reset_cooldown(ctx)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Join Voice Channel"),
                    description=_("There are other people listening."),
                )
        if dj_enabled and not vote_enabled:
            if not (can_skip or is_requester) and not is_alone:
                ctx.command.reset_cooldown(ctx)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Join Voice Channel"),
                    description=_("You need the DJ role to summon the bot."),
                )

        try:
            if (
                not ctx.author.voice.channel.permissions_for(ctx.me).connect
                or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                and userlimit(ctx.author.voice.channel)
            ):
                ctx.command.reset_cooldown(ctx)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Join Voice Channel"),
                    description=_("I don't have permission to connect to your channel."),
                )
            if not self._player_check(ctx):
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            else:
                player = lavalink.get_player(ctx.guild.id)
                if ctx.author.voice.channel == player.channel:
                    ctx.command.reset_cooldown(ctx)
                    return
                await player.move_to(ctx.author.voice.channel)
        except AttributeError:
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Join Voice Channel"),
                description=_("Connect to a voice channel first."),
            )
        except IndexError:
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Join Voice Channel"),
                description=_("Connection to Lavalink has not yet been established."),
            )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def volume(self, ctx: commands.Context, vol: int = None):
        """Set the volume, 1% - 150%."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if not vol:
            vol = await self.config.guild(ctx.guild).volume()
            embed = discord.Embed(title=_("Current Volume:"), description=str(vol) + "%")
            if not self._player_check(ctx):
                embed.set_footer(text=_("Nothing playing."))
            return await self._embed_msg(ctx, embed=embed)
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not await self._can_instaskip(ctx, ctx.author):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Change Volume"),
                    description=_("You must be in the voice channel to change the volume."),
                )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._has_dj_role(
                ctx, ctx.author
            ):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Change Volume"),
                    description=_("You need the DJ role to change the volume."),
                )
        if vol < 0:
            vol = 0
        if vol > 150:
            vol = 150
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check(ctx):
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        else:
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check(ctx):
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        embed = discord.Embed(title=_("Volume:"), description=str(vol) + "%")
        if not self._player_check(ctx):
            embed.set_footer(text=_("Nothing playing."))
        await self._embed_msg(ctx, embed=embed)
