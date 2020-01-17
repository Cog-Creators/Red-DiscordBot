import asyncio
import contextlib
import datetime
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Union, MutableMapping, Tuple

import aiohttp
import discord
import lavalink
import math
from discord.embeds import EmptyEmbed
from fuzzywuzzy import process

from redbot.cogs.audio.apis.playlist_interface import Playlist, create_playlist
from redbot.cogs.audio.audio_dataclasses import LocalPath, Query, _PARTIALLY_SUPPORTED_MUSIC_EXT
from redbot.cogs.audio.audio_logging import IS_DEBUG
from redbot.cogs.audio.cog.utils import CompositeMetaClass, _
from redbot.cogs.audio.equalizer import Equalizer
from redbot.cogs.audio.errors import (
    TrackEnqueueError,
    TooManyMatches,
    SpotifyFetchError,
    QueryUnauthorized,
)
from redbot.cogs.audio.utils import (
    rgetattr,
    remove_react,
    clear_react,
    PlaylistScope,
    humanize_scope,
    Notifier,
    track_creator,
    userlimit,
    draw_time,
    queue_duration,
    get_track_description,
    match_url,
    is_allowed,
    track_limit,
    get_track_description_unformatted,
)
from redbot.core import commands, bank
from redbot.core.utils.chat_formatting import box, humanize_number, bold, escape
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

log = logging.getLogger("red.cogs.Audio.cog.utilities")


class Utilities(metaclass=CompositeMetaClass,):
    async def error_reset(self, player: lavalink.Player):
        guild = rgetattr(player, "channel.guild.id", None)
        if not guild:
            return
        now = time.time()
        seconds_allowed = 10
        last_error = self._error_timer.setdefault(guild, now)
        if now - seconds_allowed > last_error:
            self._error_timer[guild] = 0
            self._error_counter[guild] = 0

    async def increase_error_counter(self, player: lavalink.Player) -> bool:
        guild = rgetattr(player, "channel.guild.id", None)
        if not guild:
            return False
        now = time.time()
        self._error_counter[guild] += 1
        self._error_timer[guild] = now
        return self._error_counter[guild] >= 5

    @staticmethod
    async def _players_check():
        try:
            current = next(
                (
                    player.current
                    for player in lavalink.active_players()
                    if player.current is not None
                ),
                None,
            )
            get_single_title = get_track_description_unformatted(current)
            playing_servers = len(lavalink.active_players())
        except IndexError:
            get_single_title = None
            playing_servers = 0
        return get_single_title, playing_servers

    async def _status_check(self, track, playing_servers):
        if playing_servers == 0:
            await self.bot.change_presence(activity=None)
        elif playing_servers == 1:
            await self.bot.change_presence(
                activity=discord.Activity(name=track, type=discord.ActivityType.listening)
            )
        elif playing_servers > 1:
            await self.bot.change_presence(
                activity=discord.Activity(
                    name=_("music in {} servers").format(playing_servers),
                    type=discord.ActivityType.playing,
                )
            )

    async def _localtracks_folders(
        self, ctx: commands.Context, search_subfolders=False
    ) -> Optional[List[Union[Path, LocalPath]]]:
        audio_data = LocalPath(LocalPath(None).localtrack_folder.absolute())
        if not await self._localtracks_check(ctx):
            return

        return audio_data.subfolders_in_tree() if search_subfolders else audio_data.subfolders()

    async def _folder_list(self, ctx: commands.Context, query: Query) -> Optional[List[Query]]:
        if not await self._localtracks_check(ctx):
            return
        query = Query.process_input(query)
        if not query.track.exists():
            return
        return (
            query.track.tracks_in_tree()
            if query.search_subfolders
            else query.track.tracks_in_folder()
        )

    async def _folder_tracks(
        self, ctx, player: lavalink.player_manager.Player, query: Query
    ) -> Optional[List[lavalink.rest_api.Track]]:
        if not await self._localtracks_check(ctx):
            return

        audio_data = LocalPath(None)
        try:
            query.track.path.relative_to(audio_data.to_string())
        except ValueError:
            return
        local_tracks = []
        for local_file in await self._all_folder_tracks(ctx, query):
            trackdata, called_api = await self.api_interface.fetch_track(ctx, player, local_file)
            with contextlib.suppress(IndexError):
                local_tracks.append(trackdata.tracks[0])
        return local_tracks

    async def _local_play_all(
        self, ctx: commands.Context, query: Query, from_search=False
    ) -> None:
        if not await self._localtracks_check(ctx):
            return
        if from_search:
            query = Query.process_input(query.track.to_string(), invoked_from="local folder")
        await ctx.invoke(self.search, query=query)

    async def _all_folder_tracks(
        self, ctx: commands.Context, query: Query
    ) -> Optional[List[Query]]:
        if not await self._localtracks_check(ctx):
            return

        return (
            query.track.tracks_in_tree()
            if query.search_subfolders
            else query.track.tracks_in_folder()
        )

    async def _localtracks_check(self, ctx: commands.Context) -> bool:
        folder = LocalPath(None)
        if folder.localtrack_folder.exists():
            return True
        if ctx.invoked_with != "start":
            await self._embed_msg(
                ctx, title=_("Invalid Environment"), description=_("No localtracks folder.")
            )
        return False

    async def _get_spotify_tracks(self, ctx: commands.Context, query: Query):
        if ctx.invoked_with in ["play", "genre"]:
            enqueue_tracks = True
        else:
            enqueue_tracks = False
        player = lavalink.get_player(ctx.guild.id)
        api_data = await self._check_api_tokens()

        if (
            not api_data["spotify_client_id"]
            or not api_data["spotify_client_secret"]
            or not api_data["youtube_api"]
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
        try:
            if self.play_lock[ctx.message.guild.id]:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Get Tracks"),
                    description=_("Wait until the playlist has finished loading."),
                )
        except KeyError:
            pass

        if query.single_track:
            try:
                res = await self.api_interface.spotify_query(
                    ctx, "track", query.id, skip_youtube=True, notifier=None
                )
                if not res:
                    title = _("Nothing found.")
                    embed = discord.Embed(title=title)
                    if query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                        title = _("Track is not playable.")
                        description = _(
                            "**{suffix}** is not a fully supported "
                            "format and some tracks may not play."
                        ).format(suffix=query.suffix)
                        embed = discord.Embed(title=title, description=description)
                    return await self._embed_msg(ctx, embed=embed)
            except SpotifyFetchError as error:
                self._play_lock(ctx, False)
                return await self._embed_msg(ctx, title=_(error.message).format(prefix=ctx.prefix))
            self._play_lock(ctx, False)
            try:
                if enqueue_tracks:
                    new_query = Query.process_input(res[0])
                    new_query.start_time = query.start_time
                    return await self._enqueue_tracks(ctx, new_query)
                else:
                    query = Query.process_input(res[0])
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
                                "I'm unable get a track from Lavalink at the moment, try again in a few minutes."
                            ),
                        )
                    tracks = result.tracks
                    if not tracks:
                        embed = discord.Embed(title=_("Nothing found."))
                        if query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                            embed = discord.Embed(title=_("Track is not playable."))
                            embed.description = _(
                                "**{suffix}** is not a fully supported format and some "
                                "tracks may not play."
                            ).format(suffix=query.suffix)
                        return await self._embed_msg(ctx, embed=embed)
                    single_track = tracks[0]
                    single_track.start_timestamp = query.start_time * 1000
                    single_track = [single_track]

                    return single_track

            except KeyError:
                self._play_lock(ctx, False)
                return await self._embed_msg(
                    ctx,
                    title=_("Invalid Environment"),
                    description=_(
                        "The Spotify API key or client secret has not been set properly. "
                        "\nUse `{prefix}audioset spotifyapi` for instructions."
                    ).format(prefix=ctx.prefix),
                )
        elif query.is_album or query.is_playlist:
            self._play_lock(ctx, True)
            track_list = await self._spotify_playlist(
                ctx, "album" if query.is_album else "playlist", query, enqueue_tracks
            )
            self._play_lock(ctx, False)
            return track_list
        else:
            return await self._embed_msg(
                ctx,
                title=_("Unable To Find Tracks"),
                description=_("This doesn't seem to be a supported Spotify URL or code."),
            )

    async def _enqueue_tracks(
        self, ctx: commands.Context, query: Union[Query, list], enqueue: bool = True,
    ):
        player = lavalink.get_player(ctx.guild.id)
        try:
            if self.play_lock[ctx.message.guild.id]:
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Get Tracks"),
                    description=_("Wait until the playlist has finished loading."),
                )
        except KeyError:
            self._play_lock(ctx, True)
        guild_data = await self.config.guild(ctx.guild).all()
        first_track_only = False
        single_track = None
        index = None
        playlist_data = None
        playlist_url = None
        seek = 0
        if type(query) is not list:
            if not await is_allowed(ctx.guild, f"{query}", query_obj=query):
                raise QueryUnauthorized(
                    _("{query} is not an allowed query.").format(query=query.to_string_user())
                )
            if query.single_track:
                first_track_only = True
                index = query.track_index
                if query.start_time:
                    seek = query.start_time
            try:
                result, called_api = await self.api_interface.fetch_track(ctx, player, query)
            except TrackEnqueueError:
                self._play_lock(ctx, False)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable to Get Track"),
                    description=_(
                        "I'm unable get a track from Lavalink at the moment, try again in a few minutes."
                    ),
                )
            tracks = result.tracks
            playlist_data = result.playlist_info
            if not enqueue:
                return tracks
            if not tracks:
                self._play_lock(ctx, False)
                title = _("Nothing found.")
                embed = discord.Embed(title=title)
                if result.exception_message:
                    embed.set_footer(text=result.exception_message[:2000].replace("\n", ""))
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
                        "**{suffix}** is not a fully supported format and some "
                        "tracks may not play."
                    ).format(suffix=query.suffix)
                return await self._embed_msg(ctx, embed=embed)
        else:
            tracks = query
        queue_dur = await queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        before_queue_length = len(player.queue)

        if not first_track_only and len(tracks) > 1:
            # a list of Tracks where all should be enqueued
            # this is a Spotify playlist already made into a list of Tracks or a
            # url where Lavalink handles providing all Track objects to use, like a
            # YouTube or Soundcloud playlist
            if len(player.queue) >= 10000:
                return await self._embed_msg(ctx, title=_("Queue size limit reached."))
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
                await asyncio.sleep(0)
            player.maybe_shuffle(0 if empty_queue else 1)

            if len(tracks) > track_len:
                maxlength_msg = " {bad_tracks} tracks cannot be queued.".format(
                    bad_tracks=(len(tracks) - track_len)
                )
            else:
                maxlength_msg = ""
            playlist_name = escape(playlist_data.name if playlist_data else _("No Title"))
            embed = discord.Embed(
                description=bold(f"[{playlist_name}]({playlist_url})")
                if playlist_url
                else playlist_name,
                title=_("Playlist Enqueued"),
            )
            embed.set_footer(
                text=_("Added {num} tracks to the queue.{maxlength_msg}").format(
                    num=track_len, maxlength_msg=maxlength_msg
                )
            )
            if not guild_data["shuffle"] and queue_dur > 0:
                embed.set_footer(
                    text=_(
                        "{time} until start of playlist playback: starts at #{position} in queue"
                    ).format(time=queue_total_duration, position=before_queue_length + 1)
                )
            if not player.current:
                await player.play()
            self._play_lock(ctx, False)
            message = await self._embed_msg(ctx, embed=embed)
            return tracks or message
        else:
            single_track = None
            # a ytsearch: prefixed item where we only need the first Track returned
            # this is in the case of [p]play <query>, a single Spotify url/code
            # or this is a localtrack item
            try:
                if len(player.queue) >= 10000:

                    return await self._embed_msg(ctx, title=_("Queue size limit reached."))

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
                        ctx, title=_("This track is not allowed in this server.")
                    )
                elif guild_data["maxlength"] > 0:
                    if track_limit(single_track, guild_data["maxlength"]):
                        player.add(ctx.author, single_track)
                        player.maybe_shuffle()
                        self.bot.dispatch(
                            "red_audio_track_enqueue",
                            player.channel.guild,
                            single_track,
                            ctx.author,
                        )
                    else:
                        self._play_lock(ctx, False)
                        return await self._embed_msg(ctx, title=_("Track exceeds maximum length."))

                else:
                    player.add(ctx.author, single_track)
                    player.maybe_shuffle()
                    self.bot.dispatch(
                        "red_audio_track_enqueue", player.channel.guild, single_track, ctx.author
                    )
            except IndexError:
                self._play_lock(ctx, False)
                title = _("Nothing found")
                desc = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, title=title, description=desc)
            description = get_track_description(single_track)
            embed = discord.Embed(title=_("Track Enqueued"), description=description)
            if not guild_data["shuffle"] and queue_dur > 0:
                embed.set_footer(
                    text=_("{time} until track playback: #{position} in queue").format(
                        time=queue_total_duration, position=before_queue_length + 1
                    )
                )

        if not player.current:
            await player.play()
        self._play_lock(ctx, False)
        message = await self._embed_msg(ctx, embed=embed)
        return single_track or message

    async def _spotify_playlist(
        self, ctx: commands.Context, stype: str, query: Query, enqueue: bool = False,
    ):

        player = lavalink.get_player(ctx.guild.id)
        try:
            embed1 = discord.Embed(title=_("Please wait, finding tracks..."))
            playlist_msg = await self._embed_msg(ctx, embed=embed1)
            notifier = Notifier(
                ctx,
                playlist_msg,
                {
                    "spotify": _("Getting track {num}/{total}..."),
                    "youtube": _("Matching track {num}/{total}..."),
                    "lavalink": _("Loading track {num}/{total}..."),
                    "lavalink_time": _("Approximate time remaining: {seconds}"),
                },
            )
            track_list = await self.api_interface.spotify_enqueue(
                ctx,
                stype,
                query.id,
                enqueue=enqueue,
                player=player,
                lock=self._play_lock,
                notifier=notifier,
            )
        except SpotifyFetchError as error:
            self._play_lock(ctx, False)
            return await self._embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(error.message).format(prefix=ctx.prefix),
            )
        except (RuntimeError, aiohttp.ServerDisconnectedError):
            self._play_lock(ctx, False)
            error_embed = discord.Embed(
                title=_("The connection was reset while loading the playlist.")
            )
            await self._embed_msg(ctx, embed=error_embed)
            return None
        except Exception as e:
            self._play_lock(ctx, False)
            raise e
        self._play_lock(ctx, False)
        return track_list

    async def can_manage_playlist(
        self, scope: str, playlist: Playlist, ctx: commands.Context, user, guild
    ):

        is_owner = await ctx.bot.is_owner(ctx.author)
        has_perms = False
        user_to_query = user
        guild_to_query = guild
        dj_enabled = None
        playlist_author = (
            guild.get_member(playlist.author)
            if guild
            else self.bot.get_user(playlist.author) or user
        )

        is_different_user = len({playlist.author, user_to_query.id, ctx.author.id}) != 1
        is_different_guild = True if guild_to_query is None else ctx.guild.id != guild_to_query.id

        if is_owner:
            has_perms = True
        elif playlist.scope == PlaylistScope.USER.value:
            if not is_different_user:
                has_perms = True
        elif playlist.scope == PlaylistScope.GUILD.value:
            if not is_different_guild:
                dj_enabled = self._dj_status_cache.setdefault(
                    ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
                )
                if guild.owner_id == ctx.author.id:
                    has_perms = True
                elif dj_enabled and await self._has_dj_role(ctx, ctx.author):
                    has_perms = True
                elif await ctx.bot.is_mod(ctx.author):
                    has_perms = True
                elif not dj_enabled and not is_different_user:
                    has_perms = True

        if has_perms is False:
            if hasattr(playlist, "name"):
                msg = _(
                    "You do not have the permissions to manage {name} (`{id}`) [**{scope}**]."
                ).format(
                    user=playlist_author,
                    name=playlist.name,
                    id=playlist.id,
                    scope=humanize_scope(
                        playlist.scope,
                        ctx=guild_to_query
                        if playlist.scope == PlaylistScope.GUILD.value
                        else playlist_author
                        if playlist.scope == PlaylistScope.USER.value
                        else None,
                    ),
                )
            elif playlist.scope == PlaylistScope.GUILD.value and (
                is_different_guild or dj_enabled
            ):
                msg = _(
                    "You do not have the permissions to manage that playlist in {guild}."
                ).format(guild=guild_to_query)
            elif (
                playlist.scope in [PlaylistScope.GUILD.value, PlaylistScope.USER.value]
                and is_different_user
            ):
                msg = _(
                    "You do not have the permissions to manage playlist owned by {user}."
                ).format(user=playlist_author)
            else:
                msg = _(
                    "You do not have the permissions to manage "
                    "playlists in {scope} scope.".format(scope=humanize_scope(scope, the=True))
                )

            await self._embed_msg(ctx, title=_("No access to playlist."), description=msg)
            return False
        return True

    async def _get_correct_playlist_id(
        self,
        context: commands.Context,
        matches: MutableMapping,
        scope: str,
        author: discord.User,
        guild: discord.Guild,
        specified_user: bool = False,
    ) -> Tuple[Optional[int], str]:
        """
        Parameters
        ----------
        context: commands.Context
            The context in which this is being called.
        matches: dict
            A dict of the matches found where key is scope and value is matches.
        scope:str
            The custom config scope. A value from :code:`PlaylistScope`.
        author: discord.User
            The user.
        guild: discord.Guild
            The guild.
        specified_user: bool
            Whether or not a user ID was specified via argparse.
        Returns
        -------
        Tuple[Optional[int], str]
            Tuple of Playlist ID or None if none found and original user input.
        Raises
        ------
        `TooManyMatches`
            When more than 10 matches are found or
            When multiple matches are found but none is selected.

        """
        correct_scope_matches: List[Playlist]
        original_input = matches.get("arg")
        correct_scope_matches_temp: MutableMapping = matches.get(scope)
        guild_to_query = guild.id
        user_to_query = author.id
        if not correct_scope_matches_temp:
            return None, original_input
        if scope == PlaylistScope.USER.value:
            correct_scope_matches = [
                p for p in correct_scope_matches_temp if user_to_query == p.scope_id
            ]
        elif scope == PlaylistScope.GUILD.value:
            if specified_user:
                correct_scope_matches = [
                    p
                    for p in correct_scope_matches_temp
                    if guild_to_query == p.scope_id and p.author == user_to_query
                ]
            else:
                correct_scope_matches = [
                    p for p in correct_scope_matches_temp if guild_to_query == p.scope_id
                ]
        else:
            if specified_user:
                correct_scope_matches = [
                    p for p in correct_scope_matches_temp if p.author == user_to_query
                ]
            else:
                correct_scope_matches = [p for p in correct_scope_matches_temp]

        match_count = len(correct_scope_matches)
        if match_count > 1:
            correct_scope_matches2 = [
                p for p in correct_scope_matches if p.name == str(original_input).strip()
            ]
            if correct_scope_matches2:
                correct_scope_matches = correct_scope_matches2
            elif original_input.isnumeric():
                arg = int(original_input)
                correct_scope_matches3 = [p for p in correct_scope_matches if p.id == arg]
                if correct_scope_matches3:
                    correct_scope_matches = correct_scope_matches3
        match_count = len(correct_scope_matches)
        # We done all the trimming we can with the info available time to ask the user
        if match_count > 10:
            if original_input.isnumeric():
                arg = int(original_input)
                correct_scope_matches = [p for p in correct_scope_matches if p.id == arg]
            if match_count > 10:
                raise TooManyMatches(
                    _(
                        "{match_count} playlists match {original_input}: "
                        "Please try to be more specific, or use the playlist ID."
                    ).format(match_count=match_count, original_input=original_input)
                )
        elif match_count == 1:
            return correct_scope_matches[0].id, original_input
        elif match_count == 0:
            return None, original_input

        # TODO : Convert this section to a new paged reaction menu when Toby Menus are Merged
        pos_len = 3
        playlists = f"{'#':{pos_len}}\n"
        number = 0
        for number, playlist in enumerate(correct_scope_matches, 1):
            author = self.bot.get_user(playlist.author) or playlist.author or _("Unknown")
            line = _(
                "{number}."
                "    <{playlist.name}>\n"
                " - Scope:  < {scope} >\n"
                " - ID:     < {playlist.id} >\n"
                " - Tracks: < {tracks} >\n"
                " - Author: < {author} >\n\n"
            ).format(
                number=number,
                playlist=playlist,
                scope=humanize_scope(scope),
                tracks=len(playlist.tracks),
                author=author,
            )
            playlists += line

        embed = discord.Embed(
            title=_("{playlists} playlists found, which one would you like?").format(
                playlists=number
            ),
            description=box(playlists, lang="md"),
            colour=await context.embed_colour(),
        )
        msg = await context.send(embed=embed)
        avaliable_emojis = ReactionPredicate.NUMBER_EMOJIS[1:]
        avaliable_emojis.append("🔟")
        emojis = avaliable_emojis[: len(correct_scope_matches)]
        emojis.append("\N{CROSS MARK}")
        start_adding_reactions(msg, emojis)
        pred = ReactionPredicate.with_emojis(emojis, msg, user=context.author)
        try:
            await context.bot.wait_for("reaction_add", check=pred, timeout=60)
        except asyncio.TimeoutError:
            with contextlib.suppress(discord.HTTPException):
                await msg.delete()
            raise TooManyMatches(
                _("Too many matches found and you did not select which one you wanted.")
            )
        if emojis[pred.result] == "\N{CROSS MARK}":
            with contextlib.suppress(discord.HTTPException):
                await msg.delete()
            raise TooManyMatches(
                _("Too many matches found and you did not select which one you wanted.")
            )
        with contextlib.suppress(discord.HTTPException):
            await msg.delete()
        return correct_scope_matches[pred.result].id, original_input

    async def _load_v3_playlist(
        self,
        ctx: commands.Context,
        scope: str,
        uploaded_playlist_name: str,
        uploaded_playlist_url: str,
        track_list,
        author: Union[discord.User, discord.Member],
        guild: Union[discord.Guild],
    ):
        embed1 = discord.Embed(title=_("Please wait, adding tracks..."))
        playlist_msg = await self._embed_msg(ctx, embed=embed1)
        track_count = len(track_list)
        uploaded_track_count = len(track_list)
        await asyncio.sleep(1)
        embed2 = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Loading track {num}/{total}...").format(
                num=track_count, total=uploaded_track_count
            ),
        )
        await playlist_msg.edit(embed=embed2)
        playlist = await create_playlist(
            ctx, scope, uploaded_playlist_name, uploaded_playlist_url, track_list, author, guild
        )
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        if not track_count:
            msg = _("Empty playlist {name} (`{id}`) [**{scope}**] created.").format(
                name=playlist.name, id=playlist.id, scope=scope_name
            )
        elif uploaded_track_count != track_count:
            bad_tracks = uploaded_track_count - track_count
            msg = _(
                "Added {num} tracks from the {playlist_name} playlist. {num_bad} track(s) "
                "could not be loaded."
            ).format(num=track_count, playlist_name=playlist.name, num_bad=bad_tracks)
        else:
            msg = _("Added {num} tracks from the {playlist_name} playlist.").format(
                num=track_count, playlist_name=playlist.name
            )
        embed3 = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Playlist Saved"), description=msg
        )
        await playlist_msg.edit(embed=embed3)
        database_entries = []
        time_now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        for t in track_list:
            uri = t.get("info", {}).get("uri")
            if uri:
                t = {"loadType": "V2_COMPAT", "tracks": [t], "query": uri}
                data = json.dumps(t)
                if all(k in data for k in ["loadType", "playlistInfo", "isSeekable", "isStream"]):
                    database_entries.append(
                        {
                            "query": uri,
                            "data": data,
                            "last_updated": time_now,
                            "last_fetched": time_now,
                        }
                    )
        if database_entries:
            await self.api_interface.local_cache_api.lavalink.insert(database_entries)

    async def _load_v2_playlist(
        self,
        ctx: commands.Context,
        uploaded_track_list,
        player: lavalink.player_manager.Player,
        playlist_url: str,
        uploaded_playlist_name: str,
        scope: str,
        author: Union[discord.User, discord.Member],
        guild: Union[discord.Guild],
    ):
        track_list = []
        track_count = 0
        successful_count = 0
        uploaded_track_count = len(uploaded_track_list)

        embed1 = discord.Embed(title=_("Please wait, adding tracks..."))
        playlist_msg = await self._embed_msg(ctx, embed=embed1)
        notifier = Notifier(ctx, playlist_msg, {"playlist": _("Loading track {num}/{total}...")})
        for song_url in uploaded_track_list:
            track_count += 1
            try:
                try:
                    result, called_api = await self.api_interface.fetch_track(
                        ctx, player, Query.process_input(song_url)
                    )
                except TrackEnqueueError:
                    self._play_lock(ctx, False)
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable to Get Track"),
                        description=_(
                            "I'm unable get a track from Lavalink at the moment, try again in a few "
                            "minutes."
                        ),
                    )

                track = result.tracks
            except Exception:
                continue
            try:
                track_obj = track_creator(player, other_track=track[0])
                track_list.append(track_obj)
                successful_count += 1
            except Exception:
                continue
            if (track_count % 2 == 0) or (track_count == len(uploaded_track_list)):
                await notifier.notify_user(
                    current=track_count, total=len(uploaded_track_list), key="playlist"
                )

        playlist = await create_playlist(
            ctx, scope, uploaded_playlist_name, playlist_url, track_list, author, guild
        )
        scope_name = humanize_scope(
            scope, ctx=guild if scope == PlaylistScope.GUILD.value else author
        )
        if not successful_count:
            msg = _("Empty playlist {name} (`{id}`) [**{scope}**] created.").format(
                name=playlist.name, id=playlist.id, scope=scope_name
            )
        elif uploaded_track_count != successful_count:
            bad_tracks = uploaded_track_count - successful_count
            msg = _(
                "Added {num} tracks from the {playlist_name} playlist. {num_bad} track(s) "
                "could not be loaded."
            ).format(num=successful_count, playlist_name=playlist.name, num_bad=bad_tracks)
        else:
            msg = _("Added {num} tracks from the {playlist_name} playlist.").format(
                num=successful_count, playlist_name=playlist.name
            )
        embed3 = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Playlist Saved"), description=msg
        )
        await playlist_msg.edit(embed=embed3)

    async def _maybe_update_playlist(
        self, ctx: commands.Context, player: lavalink.player_manager.Player, playlist: Playlist
    ) -> Tuple[List[lavalink.Track], List[lavalink.Track], Playlist]:
        if playlist.url is None:
            return [], [], playlist
        results = {}
        updated_tracks = await self._playlist_tracks(
            ctx, player, Query.process_input(playlist.url)
        )
        if isinstance(updated_tracks, discord.Message):
            return [], [], playlist
        if not updated_tracks:
            # No Tracks available on url Lets set it to none to avoid repeated calls here
            results["url"] = None
        if updated_tracks:  # Tracks have been updated
            results["tracks"] = updated_tracks

        old_tracks = playlist.tracks_obj
        new_tracks = [lavalink.Track(data=track) for track in updated_tracks]
        removed = list(set(old_tracks) - set(new_tracks))
        added = list(set(new_tracks) - set(old_tracks))
        if removed or added:
            await playlist.edit(results)

        return added, removed, playlist

    async def _playlist_check(self, ctx: commands.Context):
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                await self._embed_msg(ctx, title=msg, description=desc)
                return False
            try:
                if (
                    not ctx.author.voice.channel.permissions_for(ctx.me).connect
                    or not ctx.author.voice.channel.permissions_for(ctx.me).move_members
                    and userlimit(ctx.author.voice.channel)
                ):
                    await self._embed_msg(
                        ctx,
                        title=_("Unable To Get Playlists"),
                        description=_("I don't have permission to connect to your channel."),
                    )
                    return False
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except IndexError:
                await self._embed_msg(
                    ctx,
                    title=_("Unable To Get Playlists"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
                return False
            except AttributeError:
                await self._embed_msg(
                    ctx,
                    title=_("Unable To Get Playlists"),
                    description=_("Connect to a voice channel first."),
                )
                return False

        player = lavalink.get_player(ctx.guild.id)
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            await self._embed_msg(
                ctx,
                title=_("Unable To Get Playlists"),
                description=_("You must be in the voice channel to use the playlist command."),
            )
            return False
        await self._eq_check(ctx, player)
        await self._data_check(ctx)
        return True

    async def _playlist_tracks(
        self, ctx: commands.Context, player: lavalink.player_manager.Player, query: Query,
    ):
        search = query.is_search
        tracklist = []

        if query.is_spotify:
            try:
                if self.play_lock[ctx.message.guild.id]:
                    return await self._embed_msg(
                        ctx,
                        title=_("Unable To Get Tracks"),
                        description=_("Wait until the playlist has finished loading."),
                    )
            except KeyError:
                pass
            tracks = await self._get_spotify_tracks(ctx, query)

            if isinstance(tracks, discord.Message):
                return None

            if not tracks:
                embed = discord.Embed(title=_("Nothing found."))
                if query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                    embed = discord.Embed(title=_("Track is not playable."))
                    embed.description = _(
                        "**{suffix}** is not a fully supported format and some "
                        "tracks may not play."
                    ).format(suffix=query.suffix)
                return await self._embed_msg(ctx, embed=embed)
            for track in tracks:
                track_obj = track_creator(player, other_track=track)
                tracklist.append(track_obj)
                await asyncio.sleep(0)
            self._play_lock(ctx, False)
        elif query.is_search:
            try:
                result, called_api = await self.api_interface.fetch_track(ctx, player, query)
            except TrackEnqueueError:
                self._play_lock(ctx, False)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable to Get Track"),
                    description=_(
                        "I'm unable get a track from Lavalink at the moment, try again in a few "
                        "minutes."
                    ),
                )

            tracks = result.tracks
            if not tracks:
                embed = discord.Embed(title=_("Nothing found."))
                if query.is_local and query.suffix in _PARTIALLY_SUPPORTED_MUSIC_EXT:
                    embed = discord.Embed(title=_("Track is not playable."))
                    embed.description = _(
                        "**{suffix}** is not a fully supported format and some "
                        "tracks may not play."
                    ).format(suffix=query.suffix)
                return await self._embed_msg(ctx, embed=embed)
        else:
            try:
                result, called_api = await self.api_interface.fetch_track(ctx, player, query)
            except TrackEnqueueError:
                self._play_lock(ctx, False)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable to Get Track"),
                    description=_(
                        "I'm unable get a track from Lavalink at the moment, try again in a few "
                        "minutes."
                    ),
                )

            tracks = result.tracks

        if not search and len(tracklist) == 0:
            for track in tracks:
                track_obj = track_creator(player, other_track=track)
                tracklist.append(track_obj)
                await asyncio.sleep(0)
        elif len(tracklist) == 0:
            track_obj = track_creator(player, other_track=tracks[0])
            tracklist.append(track_obj)
        return tracklist

    async def _build_queue_page(
        self, ctx: commands.Context, queue: list, player: lavalink.player_manager.Player, page_num
    ):
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        autoplay = await self.config.guild(ctx.guild).auto_play()

        queue_num_pages = math.ceil(len(queue) / 10)
        queue_idx_start = (page_num - 1) * 10
        queue_idx_end = queue_idx_start + 10
        if len(player.queue) > 500:
            queue_list = "__Too many songs in the queue, only showing the first 500__.\n\n"
        else:
            queue_list = ""

        try:
            arrow = await draw_time(ctx)
        except AttributeError:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        pos = lavalink.utils.format_time(player.position)

        if player.current.is_stream:
            dur = "LIVE"
        else:
            dur = lavalink.utils.format_time(player.current.length)

        query = Query.process_input(player.current)

        if query.is_stream:
            queue_list += _("**Currently livestreaming:**\n")
            queue_list += "**[{current.title}]({current.uri})**\n".format(current=player.current)
            queue_list += _("Requested by: **{user}**").format(user=player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        elif query.is_local:
            if player.current.title != "Unknown title":
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + "**{current.author} - {current.title}**".format(current=player.current),
                        LocalPath(player.current.uri).to_string_user(),
                        _("Requested by: **{user}**\n").format(user=player.current.requester),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
            else:
                queue_list += "\n".join(
                    (
                        _("Playing: ") + LocalPath(player.current.uri).to_string_user(),
                        _("Requested by: **{user}**\n").format(user=player.current.requester),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
        else:
            queue_list += _("Playing: ")
            queue_list += "**[{current.title}]({current.uri})**\n".format(current=player.current)
            queue_list += _("Requested by: **{user}**").format(user=player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        for i, track in enumerate(queue[queue_idx_start:queue_idx_end], start=queue_idx_start):
            if i % 100 == 0:  # TODO: Improve when Toby menu's are merged
                await asyncio.sleep(0.1)

            if len(track.title) > 40:
                track_title = str(track.title).replace("[", "")
                track_title = "{}...".format((track_title[:40]).rstrip(" "))
            else:
                track_title = track.title
            req_user = track.requester
            track_idx = i + 1
            query = Query.process_input(track)

            if query.is_local:
                if track.title == "Unknown title":
                    queue_list += f"`{track_idx}.` " + ", ".join(
                        (
                            bold(LocalPath(track.uri).to_string_user()),
                            _("requested by **{user}**\n").format(user=req_user),
                        )
                    )
                else:
                    queue_list += f"`{track_idx}.` **{track.author} - {track_title}**, " + _(
                        "requested by **{user}**\n"
                    ).format(user=req_user)
            else:
                queue_list += f"`{track_idx}.` **[{track_title}]({track.uri})**, "
                queue_list += _("requested by **{user}**\n").format(user=req_user)
            await asyncio.sleep(0)

        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title="Queue for __{guild.name}__".format(guild=ctx.guild),
            description=queue_list,
        )
        if await self.config.guild(ctx.guild).thumbnail() and player.current.thumbnail:
            embed.set_thumbnail(url=player.current.thumbnail)
        queue_dur = await queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        text = _(
            "Page {page_num}/{total_pages} | {num_tracks} tracks, {num_remaining} remaining\n"
        ).format(
            page_num=humanize_number(page_num),
            total_pages=humanize_number(queue_num_pages),
            num_tracks=len(player.queue),
            num_remaining=queue_total_duration,
        )
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
        embed.set_footer(text=text)
        return embed

    @staticmethod
    async def _build_queue_search_list(queue_list, search_words):
        track_list = []
        queue_idx = 0
        for i, track in enumerate(queue_list, start=1):
            if i % 100 == 0:  # TODO: Improve when Toby menu's are merged
                await asyncio.sleep(0.1)
            queue_idx = queue_idx + 1
            if not match_url(track.uri):
                query = Query.process_input(track)
                if track.title == "Unknown title":
                    track_title = query.track.to_string_user()
                else:
                    track_title = "{} - {}".format(track.author, track.title)
            else:
                track_title = track.title

            song_info = {str(queue_idx): track_title}
            track_list.append(song_info)
            await asyncio.sleep(0)
        search_results = process.extract(search_words, track_list, limit=50)
        search_list = []
        for search, percent_match in search_results:
            for queue_position, title in search.items():
                if percent_match > 89:
                    search_list.append([queue_position, title])
        return search_list

    @staticmethod
    async def _build_queue_search_page(ctx: commands.Context, page_num, search_list):
        search_num_pages = math.ceil(len(search_list) / 10)
        search_idx_start = (page_num - 1) * 10
        search_idx_end = search_idx_start + 10
        track_match = ""
        for i, track in enumerate(
            search_list[search_idx_start:search_idx_end], start=search_idx_start
        ):
            if i % 100 == 0:  # TODO: Improve when Toby menu's are merged
                await asyncio.sleep(0.1)
            track_idx = i + 1
            if type(track) is str:
                track_location = LocalPath(track).to_string_user()
                track_match += "`{}.` **{}**\n".format(track_idx, track_location)
            else:
                track_match += "`{}.` **{}**\n".format(track[0], track[1])
            await asyncio.sleep(0)
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Matching Tracks:"), description=track_match
        )
        embed.set_footer(
            text=(_("Page {page_num}/{total_pages}") + " | {num_tracks} tracks").format(
                page_num=humanize_number(page_num),
                total_pages=humanize_number(search_num_pages),
                num_tracks=len(search_list),
            )
        )
        return embed

    async def _search_button_action(self, ctx: commands.Context, tracks, emoji, page):
        if not self._player_check(ctx):
            if self._connection_aborted:
                msg = _("Connection to Lavalink has failed.")
                description = EmptyEmbed
                if await ctx.bot.is_owner(ctx.author):
                    description = _("Please check your console or logs for details.")
                return await self._embed_msg(ctx, title=msg, description=description)
            try:
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, title=_("Connect to a voice channel first."))
            except IndexError:
                return await self._embed_msg(
                    ctx, title=_("Connection to Lavalink has not yet been established.")
                )
        player = lavalink.get_player(ctx.guild.id)
        guild_data = await self.config.guild(ctx.guild).all()
        if len(player.queue) >= 10000:
            return await self._embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )
        if not await self._currency_check(ctx, guild_data["jukebox_price"]):
            return
        try:
            if emoji == "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[0 + (page * 5)]
            elif emoji == "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[1 + (page * 5)]
            elif emoji == "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[2 + (page * 5)]
            elif emoji == "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[3 + (page * 5)]
            elif emoji == "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = tracks[4 + (page * 5)]
            else:
                search_choice = tracks[0 + (page * 5)]
        except IndexError:
            search_choice = tracks[-1]
        if getattr(search_choice, "uri", None):
            description = get_track_description(search_choice)
        else:
            search_choice = Query.process_input(search_choice)
            if search_choice.track.exists() and search_choice.track.is_dir():
                return await ctx.invoke(self.search, query=search_choice)
            elif search_choice.track.exists() and search_choice.track.is_file():
                search_choice.invoked_from = "localtrack"
            return await ctx.invoke(self.play, query=search_choice)

        songembed = discord.Embed(title=_("Track Enqueued"), description=description)
        queue_dur = await queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        before_queue_length = len(player.queue)

        if not await is_allowed(
            ctx.guild,
            (
                f"{search_choice.title} {search_choice.author} {search_choice.uri} "
                f"{str(Query.process_input(search_choice))}"
            ),
        ):
            if IS_DEBUG:
                log.debug(f"Query is not allowed in {ctx.guild} ({ctx.guild.id})")
            self._play_lock(ctx, False)
            return await self._embed_msg(ctx, title=_("This track is not allowed in this server."))
        elif guild_data["maxlength"] > 0:

            if track_limit(search_choice.length, guild_data["maxlength"]):
                player.add(ctx.author, search_choice)
                player.maybe_shuffle()
                self.bot.dispatch(
                    "red_audio_track_enqueue", player.channel.guild, search_choice, ctx.author
                )
            else:
                return await self._embed_msg(ctx, title=_("Track exceeds maximum length."))
        else:
            player.add(ctx.author, search_choice)
            player.maybe_shuffle()
            self.bot.dispatch(
                "red_audio_track_enqueue", player.channel.guild, search_choice, ctx.author
            )

        if not guild_data["shuffle"] and queue_dur > 0:
            songembed.set_footer(
                text=_("{time} until track playback: #{position} in queue").format(
                    time=queue_total_duration, position=before_queue_length + 1
                )
            )

        if not player.current:
            await player.play()
        return await self._embed_msg(ctx, embed=songembed)

    @staticmethod
    def _format_search_options(search_choice):
        query = Query.process_input(search_choice)
        description = get_track_description(search_choice)
        return description, query

    @staticmethod
    async def _build_search_page(ctx: commands.Context, tracks, page_num):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        command = ctx.invoked_with
        folder = False
        for i, track in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            try:
                query = Query.process_input(track.uri)
                if query.is_local:
                    search_list += "`{0}.` **{1}**\n[{2}]\n".format(
                        search_track_num, track.title, LocalPath(track.uri).to_string_user(),
                    )
                else:
                    search_list += "`{0}.` **[{1}]({2})**\n".format(
                        search_track_num, track.title, track.uri
                    )
            except AttributeError:
                track = Query.process_input(track)
                if track.is_local and command != "search":
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
                    if track.is_album:
                        folder = True
                elif command == "search":
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
                else:
                    search_list += "`{}.` **{}**\n".format(
                        search_track_num, track.to_string_user()
                    )
            await asyncio.sleep(0)
        if hasattr(tracks[0], "uri") and hasattr(tracks[0], "track_identifier"):
            title = _("Tracks Found:")
            footer = _("search results")
        elif folder:
            title = _("Folders Found:")
            footer = _("local folders")
        else:
            title = _("Files Found:")
            footer = _("local tracks")
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=(_("Page {page_num}/{total_pages}") + " | {num_results} {footer}").format(
                page_num=page_num,
                total_pages=search_num_pages,
                num_results=len(tracks),
                footer=footer,
            )
        )
        return embed

    async def _can_instaskip(self, ctx: commands.Context, member: discord.Member):

        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )

        if member.bot:
            return True

        if member.id == ctx.guild.owner_id:
            return True

        if dj_enabled:
            if await self._has_dj_role(ctx, member):
                return True

        if await ctx.bot.is_owner(member):
            return True

        if await ctx.bot.is_mod(member):
            return True

        if await self._channel_check(ctx):
            return True

        return False

    @staticmethod
    async def _is_alone(ctx: commands.Context):
        channel_members = rgetattr(ctx, "guild.me.voice.channel.members", [])
        nonbots = sum(m.id != ctx.author.id for m in channel_members if not m.bot)
        return nonbots < 1

    async def _has_dj_role(self, ctx: commands.Context, member: discord.Member):
        dj_role = self._dj_role_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_role()
        )
        dj_role_obj = ctx.guild.get_role(dj_role)
        return dj_role_obj in ctx.guild.get_member(member.id).roles

    @staticmethod
    async def is_requester(ctx: commands.Context, member: discord.Member):
        try:
            player = lavalink.get_player(ctx.guild.id)
            log.debug(f"Current requester is {player.current}")
            return player.current.requester.id == member.id
        except Exception as e:
            log.error(e)
        return False

    async def _skip_action(self, ctx: commands.Context, skip_to_track: int = None):
        player = lavalink.get_player(ctx.guild.id)
        autoplay = await self.config.guild(player.channel.guild).auto_play()
        if not player.current or (not player.queue and not autoplay):
            try:
                pos, dur = player.position, player.current.length
            except AttributeError:
                return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
            time_remain = lavalink.utils.format_time(dur - pos)
            if player.current.is_stream:
                embed = discord.Embed(title=_("There's nothing in the queue."))
                embed.set_footer(
                    text=_("Currently livestreaming {track}").format(track=player.current.title)
                )
            else:
                embed = discord.Embed(title=_("There's nothing in the queue."))
                embed.set_footer(
                    text=_("{time} left on {track}").format(
                        time=time_remain, track=player.current.title
                    )
                )
            return await self._embed_msg(ctx, embed=embed)
        elif autoplay and not player.queue:
            embed = discord.Embed(
                title=_("Track Skipped"), description=get_track_description(player.current)
            )
            await self._embed_msg(ctx, embed=embed)
            return await player.skip()

        queue_to_append = []
        if skip_to_track is not None and skip_to_track != 1:
            if skip_to_track < 1:
                return await self._embed_msg(
                    ctx, title=_("Track number must be equal to or greater than 1.")
                )
            elif skip_to_track > len(player.queue):
                return await self._embed_msg(
                    ctx,
                    title=_(
                        "There are only {queuelen} songs currently queued.".format(
                            queuelen=len(player.queue)
                        )
                    ),
                )
            embed = discord.Embed(
                title=_("{skip_to_track} Tracks Skipped".format(skip_to_track=skip_to_track))
            )
            await self._embed_msg(ctx, embed=embed)
            if player.repeat:
                queue_to_append = player.queue[0 : min(skip_to_track - 1, len(player.queue) - 1)]
            player.queue = player.queue[
                min(skip_to_track - 1, len(player.queue) - 1) : len(player.queue)
            ]
        else:
            embed = discord.Embed(
                title=_("Track Skipped"), description=get_track_description(player.current)
            )
            await self._embed_msg(ctx, embed=embed)
        self.bot.dispatch("red_audio_skip_track", player.channel.guild, player.current, ctx.author)
        await player.play()
        player.queue += queue_to_append

    @staticmethod
    async def _apply_gain(guild_id: int, band, gain):
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": band, "gain": gain}],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    @staticmethod
    async def _apply_gains(guild_id: int, gains):
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": x, "gain": y} for x, y in enumerate(gains)],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    async def _channel_check(self, ctx: commands.Context):
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return False
        try:
            in_channel = sum(
                not m.bot for m in ctx.guild.get_member(self.bot.user.id).voice.channel.members
            )
        except AttributeError:
            return False

        if not ctx.author.voice:
            user_channel = None
        else:
            user_channel = ctx.author.voice.channel

        if in_channel == 0 and user_channel:
            if (
                (player.channel != user_channel)
                and not player.current
                and player.position == 0
                and len(player.queue) == 0
            ):
                await player.move_to(user_channel)
                return True
        else:
            return False

    async def _check_api_tokens(self):
        spotify = await self.bot.get_shared_api_tokens("spotify")
        youtube = await self.bot.get_shared_api_tokens("youtube")
        return {
            "spotify_client_id": spotify.get("client_id", ""),
            "spotify_client_secret": spotify.get("client_secret", ""),
            "youtube_api": youtube.get("api_key", ""),
        }

    async def _check_external(self):
        external = await self.config.use_external_lavalink()
        if not external:
            if self._manager is not None:
                await self._manager.shutdown()
            await self.config.use_external_lavalink.set(True)
            return True
        else:
            return False

    async def _clear_react(self, message: discord.Message, emoji: MutableMapping = None):
        """Non blocking version of clear_react."""
        return self.bot.loop.create_task(clear_react(self.bot, message, emoji))

    async def _currency_check(self, ctx: commands.Context, jukebox_price: int):
        jukebox = await self.config.guild(ctx.guild).jukebox()
        if jukebox and not await self._can_instaskip(ctx, ctx.author):
            can_spend = await bank.can_spend(ctx.author, jukebox_price)
            if can_spend:
                await bank.withdraw_credits(ctx.author, jukebox_price)
            else:
                credits_name = await bank.get_currency_name(ctx.guild)
                bal = await bank.get_balance(ctx.author)
                await self._embed_msg(
                    ctx,
                    title=_("Not enough {currency}").format(currency=credits_name),
                    description=_(
                        "{required_credits} {currency} required, but you have {bal}."
                    ).format(
                        currency=credits_name,
                        required_credits=humanize_number(jukebox_price),
                        bal=humanize_number(bal),
                    ),
                )
            return can_spend
        else:
            return True

    async def _data_check(self, ctx: commands.Context):
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        volume = await self.config.guild(ctx.guild).volume()
        shuffle_bumped = await self.config.guild(ctx.guild).shuffle_bumped()
        player.repeat = repeat
        player.shuffle = shuffle
        player.shuffle_bumped = shuffle_bumped
        if player.volume != volume:
            await player.set_volume(volume)

    async def _embed_msg(self, ctx: commands.Context, **kwargs):
        colour = kwargs.get("colour") or kwargs.get("color") or await self.bot.get_embed_color(ctx)
        error = kwargs.get("error", False)
        success = kwargs.get("success", False)
        title = kwargs.get("title", EmptyEmbed) or EmptyEmbed
        _type = kwargs.get("type", "rich") or "rich"
        url = kwargs.get("url", EmptyEmbed) or EmptyEmbed
        description = kwargs.get("description", EmptyEmbed) or EmptyEmbed
        timestamp = kwargs.get("timestamp")
        footer = kwargs.get("footer")
        thumbnail = kwargs.get("thumbnail")
        contents = dict(title=title, type=_type, url=url, description=description)
        embed = kwargs.get("embed").to_dict() if hasattr(kwargs.get("embed"), "to_dict") else {}
        colour = embed.get("color") if embed.get("color") else colour
        contents.update(embed)
        if timestamp and isinstance(timestamp, datetime.datetime):
            contents["timestamp"] = timestamp
        embed = discord.Embed.from_dict(contents)
        embed.color = colour
        if footer:
            embed.set_footer(text=footer)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return await ctx.send(embed=embed)

    async def _eq_check(self, ctx: commands.Context, player: lavalink.Player):
        eq = player.fetch("eq", Equalizer())

        config_bands = await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands()
        if not config_bands:
            config_bands = eq.bands
            await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)

        if eq.bands != config_bands:
            band_num = list(range(0, eq._band_count))
            band_value = config_bands
            eq_dict = {}
            for k, v in zip(band_num, band_value):
                eq_dict[k] = v
            for band, value in eq_dict.items():
                eq.set_gain(band, value)
            player.store("eq", eq)
            await self._apply_gains(ctx.guild.id, config_bands)

    async def _eq_interact(
        self, ctx: commands.Context, player: lavalink.Player, eq, message, selected
    ):
        player.store("eq", eq)
        emoji = {
            "far_left": "\N{BLACK LEFT-POINTING TRIANGLE}",
            "one_left": "\N{LEFTWARDS BLACK ARROW}",
            "max_output": "\N{BLACK UP-POINTING DOUBLE TRIANGLE}",
            "output_up": "\N{UP-POINTING SMALL RED TRIANGLE}",
            "output_down": "\N{DOWN-POINTING SMALL RED TRIANGLE}",
            "min_output": "\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}",
            "one_right": "\N{BLACK RIGHTWARDS ARROW}",
            "far_right": "\N{BLACK RIGHT-POINTING TRIANGLE}",
            "reset": "\N{BLACK CIRCLE FOR RECORD}",
            "info": "\N{INFORMATION SOURCE}",
        }
        selector = f'{" " * 8}{"   " * selected}^^'
        try:
            await message.edit(content=box(f"{eq.visualise()}\n{selector}", lang="ini"))
        except discord.errors.NotFound:
            return
        try:
            (react_emoji, react_user) = await self._get_eq_reaction(ctx, message, emoji)
        except TypeError:
            return

        if not react_emoji:
            await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands.set(eq.bands)
            await self._clear_react(message, emoji)

        if react_emoji == "\N{LEFTWARDS BLACK ARROW}":
            await remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, eq, message, max(selected - 1, 0))

        if react_emoji == "\N{BLACK RIGHTWARDS ARROW}":
            await remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, eq, message, min(selected + 1, 14))

        if react_emoji == "\N{UP-POINTING SMALL RED TRIANGLE}":
            await remove_react(message, react_emoji, react_user)
            _max = "{:.2f}".format(min(eq.get_gain(selected) + 0.1, 1.0))
            eq.set_gain(selected, float(_max))
            await self._apply_gain(ctx.guild.id, selected, _max)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{DOWN-POINTING SMALL RED TRIANGLE}":
            await remove_react(message, react_emoji, react_user)
            _min = "{:.2f}".format(max(eq.get_gain(selected) - 0.1, -0.25))
            eq.set_gain(selected, float(_min))
            await self._apply_gain(ctx.guild.id, selected, _min)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK UP-POINTING DOUBLE TRIANGLE}":
            await remove_react(message, react_emoji, react_user)
            _max = 1.0
            eq.set_gain(selected, _max)
            await self._apply_gain(ctx.guild.id, selected, _max)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}":
            await remove_react(message, react_emoji, react_user)
            _min = -0.25
            eq.set_gain(selected, _min)
            await self._apply_gain(ctx.guild.id, selected, _min)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK LEFT-POINTING TRIANGLE}":
            await remove_react(message, react_emoji, react_user)
            selected = 0
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}":
            await remove_react(message, react_emoji, react_user)
            selected = 14
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK CIRCLE FOR RECORD}":
            await remove_react(message, react_emoji, react_user)
            for band in range(eq._band_count):
                eq.set_gain(band, 0.0)
            await self._apply_gains(ctx.guild.id, eq.bands)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{INFORMATION SOURCE}":
            await remove_react(message, react_emoji, react_user)
            await ctx.send_help(self.eq)
            await self._eq_interact(ctx, player, eq, message, selected)

    @staticmethod
    async def _eq_msg_clear(eq_message: discord.Message):
        if eq_message is not None:
            with contextlib.suppress(discord.HTTPException):
                await eq_message.delete()

    async def _get_eq_reaction(self, ctx: commands.Context, message: discord.Message, emoji):
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == message.id
                and u.id == ctx.author.id
                and r.emoji in emoji.values(),
                timeout=30,
            )
        except asyncio.TimeoutError:
            await self._clear_react(message, emoji)
            return None
        else:
            return reaction.emoji, user

    def _play_lock(self, ctx: commands.Context, tf):
        if tf:
            self.play_lock[ctx.message.guild.id] = True
        else:
            self.play_lock[ctx.message.guild.id] = False

    def _player_check(self, ctx: commands.Context):
        if self._connection_aborted:
            return False
        try:
            lavalink.get_player(ctx.guild.id)
            return True
        except IndexError:
            return False
        except KeyError:
            return False

    async def _process_db(self, ctx: commands.Context):
        await self.api_interface.run_tasks(ctx)

    async def _close_database(self):
        await self.api_interface.run_all_pending_tasks()
        self.api_interface.close()

    @staticmethod
    async def _genre_search_button_action(
        ctx: commands.Context, options, emoji, page, playlist=False
    ):
        try:
            if emoji == "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[0 + (page * 5)]
            elif emoji == "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[1 + (page * 5)]
            elif emoji == "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[2 + (page * 5)]
            elif emoji == "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[3 + (page * 5)]
            elif emoji == "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}":
                search_choice = options[4 + (page * 5)]
            else:
                search_choice = options[0 + (page * 5)]
        except IndexError:
            search_choice = options[-1]
        if not playlist:
            return list(search_choice.items())[0]
        else:
            return search_choice.get("uri")

    @staticmethod
    async def _build_genre_search_page(
        ctx: commands.Context, tracks, page_num, title, playlist=False
    ):
        search_num_pages = math.ceil(len(tracks) / 5)
        search_idx_start = (page_num - 1) * 5
        search_idx_end = search_idx_start + 5
        search_list = ""
        for i, entry in enumerate(tracks[search_idx_start:search_idx_end], start=search_idx_start):
            search_track_num = i + 1
            if search_track_num > 5:
                search_track_num = search_track_num % 5
            if search_track_num == 0:
                search_track_num = 5
            if playlist:
                name = "**[{}]({})** - {}".format(
                    entry.get("name"),
                    entry.get("url"),
                    str(entry.get("tracks")) + " " + _("tracks"),
                )
            else:
                name = f"{list(entry.keys())[0]}"
            search_list += "`{}.` {}\n".format(search_track_num, name)
            await asyncio.sleep(0)

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=title, description=search_list
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages}").format(
                page_num=page_num, total_pages=search_num_pages
            )
        )
        return embed

    @staticmethod
    async def _build_playlist_list_page(ctx: commands.Context, page_num, abc_names, scope):
        plist_num_pages = math.ceil(len(abc_names) / 5)
        plist_idx_start = (page_num - 1) * 5
        plist_idx_end = plist_idx_start + 5
        plist = ""
        for i, playlist_info in enumerate(
            abc_names[plist_idx_start:plist_idx_end], start=plist_idx_start
        ):
            item_idx = i + 1
            plist += "`{}.` {}".format(item_idx, playlist_info)
            await asyncio.sleep(0)
        embed = discord.Embed(
            colour=await ctx.embed_colour(),
            title=_("Playlists for {scope}:").format(scope=scope),
            description=plist,
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages} | {num} playlists.").format(
                page_num=page_num, total_pages=plist_num_pages, num=len(abc_names)
            )
        )
        return embed

    @staticmethod
    async def _build_local_search_list(to_search, search_words):
        to_search_string = {i.track.name for i in to_search}
        search_results = process.extract(search_words, to_search_string, limit=50)
        search_list = []
        for track_match, percent_match in search_results:
            if percent_match > 60:
                search_list.extend(
                    [i.track.to_string_user() for i in to_search if i.track.name == track_match]
                )
            await asyncio.sleep(0)
        return search_list
