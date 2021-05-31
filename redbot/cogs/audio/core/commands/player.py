import contextlib
import logging
import math
import time
from pathlib import Path
from typing import List, MutableMapping

import discord
import lavalink
from discord.embeds import EmptyEmbed
from redbot.core import commands
from redbot.core.commands import UserInputOptional
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils._dpy_menus_utils import dpymenu
from redbot.core.utils.menus import close_menu, menu, next_page, prev_page

from ...audio_dataclasses import _PARTIALLY_SUPPORTED_MUSIC_EXT, Query
from ...audio_logging import IS_DEBUG
from ...converters import MultiLineConverter
from ...errors import DatabaseError, QueryUnauthorized, SpotifyFetchError, TrackEnqueueError
from ..abc import MixinMeta
from ..cog_utils import ENABLED_TITLE, CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Commands.player")
_ = Translator("Audio", Path(__file__))


class PlayerCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.command(name="play")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def command_play(self, ctx: commands.Context, *, queries: MultiLineConverter):
        """Play the specified track or search for a close match.

        To play a local track, the query should be `<parentfolder>\\<filename>`.
        If you are the bot owner, use `[p]audioset ll info` to display your localtracks path.

        To play multiple tracks with a single command use the following syntax (Shift + Enter usually will cause you to start a new line):

        [p]play Song1
        Song2
        Song3
        SongNth
        """
        queries: List[Query]
        for query in queries:
            restrict = await self.config_cache.url_restrict.get_context_value(ctx.guild)
            if restrict and self.match_url(str(query)):
                valid_url = self.is_url_allowed(str(query))
                if not valid_url:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("That URL is not allowed."),
                    )
            elif not await self.is_query_allowed(
                self.config_cache, ctx, f"{query}", query_obj=query
            ):
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("That track is not allowed."),
                )
            can_skip = await self._can_instaskip(ctx, ctx.author)
            if await self.config_cache.dj_status.get_context_value(ctx.guild) and not can_skip:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("You need the DJ role to queue tracks."),
                )
            if not self._player_check(ctx):
                if self.lavalink_connection_aborted:
                    msg = _("Connection to Lavalink has failed")
                    desc = EmptyEmbed
                    if await self.bot.is_owner(ctx.author):
                        desc = _("Please check your console or logs for details.")
                    return await self.send_embed_msg(ctx, title=msg, description=desc)
                try:
                    if not self.can_join_and_speak(ctx.author.voice.channel) or self.is_vc_full(
                        ctx.author.voice.channel
                    ):
                        return await self.send_embed_msg(
                            ctx,
                            title=_("Unable To Play Tracks"),
                            description=_(
                                "I don't have permission to connect and speak in your channel."
                            ),
                        )
                    await lavalink.connect(
                        ctx.author.voice.channel,
                        deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                    )
                except AttributeError:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("Connect to a voice channel first."),
                    )
                except IndexError:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("Connection to Lavalink has not yet been established."),
                    )
            player = lavalink.get_player(ctx.guild.id)
            player.store("notify_channel", ctx.channel.id)
            await self._eq_check(ctx, player)
            await self.set_player_settings(ctx)
            if (
                not ctx.author.voice or ctx.author.voice.channel != player.channel
            ) and not can_skip:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("You must be in the voice channel to use the play command."),
                )
            if not query.valid:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("No tracks found for `{query}`.").format(
                        query=query.to_string_user()
                    ),
                )
            if len(player.queue) >= await self.config_cache.max_queue_size.get_context_value(
                player.guild
            ):
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Queue size limit reached."),
                )

            if not await self.maybe_charge_requester(
                ctx, await self.config_cache.jukebox_price.get_context_value(ctx.guild)
            ):
                return
            if query.is_spotify:
                await self._get_spotify_tracks(ctx, query)
                if len(queries) > 1:
                    continue
                return
            try:
                await self._enqueue_tracks(ctx, query)
            except QueryUnauthorized as err:
                return await self.send_embed_msg(
                    ctx, title=_("Unable To Play Tracks"), description=err.message
                )
            except Exception as e:
                self.update_player_lock(ctx, False)
                raise e

    @commands.command(name="bumpplay")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def command_bumpplay(
        self, ctx: commands.Context, play_now: UserInputOptional[bool] = False, *, query: str
    ):
        """Force play a URL or search for a track."""
        query = Query.process_input(query, self.local_folder_current_path)
        if not query.single_track:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Bump Track"),
                description=_("Only single tracks work with bump play."),
            )
        restrict = await self.config_cache.url_restrict.get_context_value(ctx.guild)
        if restrict and self.match_url(str(query)):
            valid_url = self.is_url_allowed(str(query))
            if not valid_url:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("That URL is not allowed."),
                )
        elif not await self.is_query_allowed(self.config_cache, ctx, f"{query}", query_obj=query):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("That track is not allowed.")
            )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if await self.config_cache.dj_status.get_context_value(ctx.guild) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You need the DJ role to queue tracks."),
            )
        if not self._player_check(ctx):
            if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await self.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=msg, description=desc)
            try:
                if not self.can_join_and_speak(ctx.author.voice.channel) or self.is_vc_full(
                    ctx.author.voice.channel
                ):
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_(
                            "I don't have permission to connect and speak in your channel."
                        ),
                    )
                await lavalink.connect(
                    ctx.author.voice.channel,
                    deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                )
            except AttributeError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        await self._eq_check(ctx, player)
        await self.set_player_settings(ctx)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the play command."),
            )
        if not query.valid:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("No tracks found for `{query}`.").format(
                    query=query.to_string_user()
                ),
            )
        if len(player.queue) >= await self.config_cache.max_queue_size.get_context_value(
            player.guild
        ):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )

        if not await self.maybe_charge_requester(
            ctx, await self.config_cache.jukebox_price.get_context_value(ctx.guild)
        ):
            return
        try:
            if query.is_spotify:
                tracks = await self._get_spotify_tracks(ctx, query)
            else:
                tracks = await self._enqueue_tracks(ctx, query, enqueue=False)
        except QueryUnauthorized as err:
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=err.message
            )
        except Exception as e:
            self.update_player_lock(ctx, False)
            raise e
        if isinstance(tracks, discord.Message):
            return
        elif not tracks:
            self.update_player_lock(ctx, False)
            title = _("Unable To Play Tracks")
            desc = _("No tracks found for `{query}`.").format(query=query.to_string_user())
            embed = discord.Embed(title=title, description=desc)
            if (
                await self.config_cache.external_lavalink_server.get_context_value(ctx.guild)
                and query.is_local
            ):
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
                    "**{suffix}** is not a fully supported format and some tracks may not play."
                ).format(suffix=query.suffix)
            return await self.send_embed_msg(ctx, embed=embed)
        queue_dur = await self.track_remaining_duration(ctx)
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
        query = Query.process_input(single_track, self.local_folder_current_path)
        if not await self.is_query_allowed(
            self.config_cache,
            ctx,
            f"{single_track.title} {single_track.author} {single_track.uri} {str(query)}",
            query_obj=query,
        ):
            if IS_DEBUG:
                log.debug("Query is not allowed in %r (%d)", ctx.guild.name, ctx.guild.id)
            self.update_player_lock(ctx, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("This track is not allowed in this server."),
            )
        elif (
            max_length := await self.config_cache.max_track_length.get_context_value(ctx.guild)
        ) > 0:
            if self.is_track_length_allowed(single_track, max_length):
                single_track.requester = ctx.author
                single_track.extras.update(
                    {
                        "enqueue_time": int(time.time()),
                        "vc": player.channel.id,
                        "requester": ctx.author.id,
                    }
                )
                player.queue.insert(0, single_track)
                player.maybe_shuffle()
                self.bot.dispatch(
                    "red_audio_track_enqueue", player.guild, single_track, ctx.author
                )
            else:
                self.update_player_lock(ctx, False)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Track exceeds maximum length."),
                )

        else:
            single_track.requester = ctx.author
            single_track.extras["bumped"] = True
            single_track.extras.update(
                {
                    "enqueue_time": int(time.time()),
                    "vc": player.channel.id,
                    "requester": ctx.author.id,
                }
            )
            player.queue.insert(0, single_track)
            player.maybe_shuffle()
            self.bot.dispatch("red_audio_track_enqueue", player.guild, single_track, ctx.author)
        description = await self.get_track_description(
            single_track, self.local_folder_current_path
        )
        footer = None
        if (
            not play_now
            and not await self.config_cache.shuffle.get_context_value(ctx.guild)
            and queue_dur > 0
        ):
            footer = _("{time} until track playback: #1 in queue").format(
                time=self.format_time(queue_dur)
            )
        await self.send_embed_msg(
            ctx, title=_("Track Enqueued"), description=description, footer=footer
        )

        if not player.current:
            await player.play()
        elif play_now:
            await player.skip()

        self.update_player_lock(ctx, False)

    @commands.command(name="genre")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def command_genre(self, ctx: commands.Context):
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
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
        }
        playlist_search_controls = {
            "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}": _playlist_search_menu,
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
        }

        api_data = await self._check_api_tokens()
        if any([not api_data["spotify_client_id"], not api_data["spotify_client_secret"]]):
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(
                    "The owner needs to set the Spotify client ID and Spotify client secret, "
                    "before Spotify URLs or codes can be used. "
                    "\nSee `{prefix}audioset spotifyapi` for instructions."
                ).format(prefix=ctx.prefix),
            )
        elif not api_data["youtube_api"]:
            return await self.send_embed_msg(
                ctx,
                title=_("Invalid Environment"),
                description=_(
                    "The owner needs to set the YouTube API key before Spotify URLs or "
                    "codes can be used.\nSee `{prefix}audioset youtubeapi` for instructions."
                ).format(prefix=ctx.prefix),
            )
        if await self.config_cache.dj_status.get_context_value(
            ctx.guild
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You need the DJ role to queue tracks."),
            )
        if not self._player_check(ctx):
            if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await self.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=msg, description=desc)
            try:
                if not self.can_join_and_speak(ctx.author.voice.channel) or self.is_vc_full(
                    ctx.author.voice.channel
                ):
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_(
                            "I don't have permission to connect and speak in your channel."
                        ),
                    )
                await lavalink.connect(
                    ctx.author.voice.channel,
                    deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                )
            except AttributeError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        await self._eq_check(ctx, player)
        await self.set_player_settings(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the genre command."),
            )
        try:
            category_list = await self.api_interface.spotify_api.get_categories(ctx=ctx)
        except SpotifyFetchError as error:
            return await self.send_embed_msg(
                ctx,
                title=_("No categories found"),
                description=error.message.format(prefix=ctx.prefix),
            )
        if not category_list:
            return await self.send_embed_msg(ctx, title=_("No categories found, try again later."))
        len_folder_pages = math.ceil(len(category_list) / 5)
        category_search_page_list = []
        async for page_num in AsyncIter(range(1, len_folder_pages + 1)):
            embed = await self._build_genre_search_page(
                ctx, category_list, page_num, _("Categories")
            )
            category_search_page_list.append(embed)
        cat_menu_output = await menu(ctx, category_search_page_list, category_search_controls)
        if not cat_menu_output:
            return await self.send_embed_msg(
                ctx, title=_("No categories selected, try again later.")
            )
        category_name, category_pick = cat_menu_output
        playlists_list = await self.api_interface.spotify_api.get_playlist_from_category(
            category_pick, ctx=ctx
        )
        if not playlists_list:
            return await self.send_embed_msg(ctx, title=_("No categories found, try again later."))
        len_folder_pages = math.ceil(len(playlists_list) / 5)
        playlists_search_page_list = []
        async for page_num in AsyncIter(range(1, len_folder_pages + 1)):
            embed = await self._build_genre_search_page(
                ctx,
                playlists_list,
                page_num,
                _("Playlists for {friendly_name}").format(friendly_name=category_name),
                playlist=True,
            )
            playlists_search_page_list.append(embed)
        playlists_pick = await menu(ctx, playlists_search_page_list, playlist_search_controls)
        query = Query.process_input(playlists_pick, self.local_folder_current_path)
        if not query.valid:
            return await self.send_embed_msg(ctx, title=_("No tracks to play."))
        if len(player.queue) >= await self.config_cache.max_queue_size.get_context_value(
            player.guild
        ):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )
        if not await self.maybe_charge_requester(
            ctx, await self.config_cache.jukebox_price.get_context_value(ctx.guild)
        ):
            return
        if query.is_spotify:
            return await self._get_spotify_tracks(ctx, query)
        return await self.send_embed_msg(
            ctx, title=_("Couldn't find tracks for the selected playlist.")
        )

    @commands.command(name="autoplay")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.mod_or_permissions(manage_guild=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def command_autoplay(self, ctx: commands.Context):
        """Starts auto play."""
        if await self.config_cache.dj_status.get_context_value(
            ctx.guild
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You need the DJ role to queue tracks."),
            )
        if await self.config_cache.disconnect.get_global() is True:
            await self.config_cache.disconnect.set_guild(ctx.guild, True)
            await self.config_cache.autoplay.set_guild(ctx.guild, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Setting Not Changed"),
                description=_(
                    "Auto-disconnection at queue end: {true_or_false}\n"
                    "Auto-play has been disabled."
                    "\n\n**Reason**: The bot owner has disabled this feature."
                ).format(true_or_false=ENABLED_TITLE),
            )
        if not self._player_check(ctx):
            if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await self.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=msg, description=desc)
            try:
                if not self.can_join_and_speak(ctx.author.voice.channel) or self.is_vc_full(
                    ctx.author.voice.channel
                ):
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_(
                            "I don't have permission to connect and speak in your channel."
                        ),
                    )
                await lavalink.connect(
                    ctx.author.voice.channel,
                    deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                )
            except AttributeError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        await self._eq_check(ctx, player)
        await self.set_player_settings(ctx)
        if (
            not ctx.author.voice or ctx.author.voice.channel != player.channel
        ) and not await self._can_instaskip(ctx, ctx.author):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the autoplay command."),
            )
        if len(player.queue) >= await self.config_cache.max_queue_size.get_context_value(
            player.guild
        ):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )
        if not await self.maybe_charge_requester(
            ctx, await self.config_cache.jukebox_price.get_context_value(ctx.guild)
        ):
            return
        try:
            await self.api_interface.autoplay(player, self.playlist_api)
        except DatabaseError:
            notify_channel = player.fetch("notify_channel")
            if notify_channel:
                notify_channel = self.bot.get_channel(notify_channel)
                await self.send_embed_msg(notify_channel, title=_("Couldn't get a valid track."))
            return
        except TrackEnqueueError:
            self.update_player_lock(ctx, False)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable to Get Track"),
                description=_(
                    "I'm unable to get a track from Lavalink at the moment, try again in a few "
                    "minutes."
                ),
            )
        except Exception as e:
            self.update_player_lock(ctx, False)
            raise e

        if not await self.config_cache.autoplay.get_context_value(ctx.guild):
            await ctx.invoke(self.command_audioset_guild_autoplay_toggle)
        if not await self.config_cache.notify.get_context_value(ctx.guild) and not player.fetch(
            "autoplay_notified", False
        ):
            pass
        elif player.current:
            await self.send_embed_msg(ctx, title=_("Adding a track to queue."))

    @commands.command(name="search")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    @commands.cooldown(1, 15, commands.BucketType.member)
    async def command_search(self, ctx: commands.Context, *, query: str):
        """Pick a track with a search.

        Use `[p]search list <search term>` to queue all tracks found on YouTube. Use `[p]search sc
        <search term>` to search on SoundCloud instead of YouTube.
        """

        if not isinstance(query, (str, list, Query)):
            raise RuntimeError(
                f"Expected 'query' to be a string, list or Query object but received: {type(query)} - this is an unexpected argument type, please report it."
            )

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
            "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}": next_page,
        }

        if not self._player_check(ctx):
            if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await self.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=msg, description=desc)
            try:
                if not self.can_join_and_speak(ctx.author.voice.channel) or self.is_vc_full(
                    ctx.author.voice.channel
                ):
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Search For Tracks"),
                        description=_(
                            "I don't have permission to connect and speak in your channel."
                        ),
                    )
                await lavalink.connect(
                    ctx.author.voice.channel,
                    deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                )
            except AttributeError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Search For Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Search For Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Search For Tracks"),
                description=_("You must be in the voice channel to enqueue tracks."),
            )
        await self._eq_check(ctx, player)
        await self.set_player_settings(ctx)

        before_queue_length = len(player.queue)

        if not isinstance(query, list):
            query = Query.process_input(query, self.local_folder_current_path)
            restrict = await self.config_cache.url_restrict.get_context_value(ctx.guild)
            if restrict and self.match_url(str(query)):
                valid_url = self.is_url_allowed(str(query))
                if not valid_url:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("That URL is not allowed."),
                    )
            if not await self.is_query_allowed(
                self.config_cache, ctx, f"{query}", query_obj=query
            ):
                return await self.send_embed_msg(
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
                        self.update_player_lock(ctx, False)
                        return await self.send_embed_msg(
                            ctx,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable to get a track from Lavalink at the moment, "
                                "try again in a few minutes."
                            ),
                        )
                    except Exception as e:
                        self.update_player_lock(ctx, False)
                        raise e

                    tracks = result.tracks
                else:
                    try:
                        query.search_subfolders = True
                        tracks = await self.get_localtrack_folder_tracks(ctx, player, query)
                    except TrackEnqueueError:
                        self.update_player_lock(ctx, False)
                        return await self.send_embed_msg(
                            ctx,
                            title=_("Unable to Get Track"),
                            description=_(
                                "I'm unable to get a track from Lavalink at the moment, "
                                "try again in a few minutes."
                            ),
                        )
                    except Exception as e:
                        self.update_player_lock(ctx, False)
                        raise e
                if not tracks:
                    embed = discord.Embed(title=_("Nothing found."))
                    if (
                        await self.config_cache.external_lavalink_server.get_context_value(
                            ctx.guild
                        )
                        and query.is_local
                    ):
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
                    return await self.send_embed_msg(ctx, embed=embed)
                queue_dur = await self.queue_duration(ctx)
                queue_total_duration = self.format_time(queue_dur)
                if await self.config_cache.dj_status.get_context_value(ctx.guild) and not can_skip:
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_("You need the DJ role to queue tracks."),
                    )
                track_len = 0
                empty_queue = not player.queue
                max_queue_length = await self.config_cache.max_queue_size.get_context_value(
                    player.guild
                )
                async for track in AsyncIter(tracks):
                    if len(player.queue) >= max_queue_length:
                        continue
                    query = Query.process_input(track, self.local_folder_current_path)
                    if not await self.is_query_allowed(
                        self.config_cache,
                        ctx,
                        f"{track.title} {track.author} {track.uri} " f"{str(query)}",
                        query_obj=query,
                    ):
                        if IS_DEBUG:
                            log.debug(
                                "Query is not allowed in %r (%d)", ctx.guild.name, ctx.guild.id
                            )
                        continue
                    elif (
                        max_length := await self.config_cache.max_track_length.get_context_value(
                            ctx.guild
                        )
                    ) > 0:
                        if self.is_track_length_allowed(track, max_length):
                            track_len += 1
                            track.extras.update(
                                {
                                    "enqueue_time": int(time.time()),
                                    "vc": player.channel.id,
                                    "requester": ctx.author.id,
                                }
                            )
                            player.add(ctx.author, track)
                            self.bot.dispatch(
                                "red_audio_track_enqueue", player.guild, track, ctx.author
                            )
                    else:
                        track_len += 1
                        track.extras.update(
                            {
                                "enqueue_time": int(time.time()),
                                "vc": player.channel.id,
                                "requester": ctx.author.id,
                            }
                        )
                        player.add(ctx.author, track)
                        self.bot.dispatch(
                            "red_audio_track_enqueue", player.guild, track, ctx.author
                        )
                    if not player.current:
                        await player.play()
                player.maybe_shuffle(0 if empty_queue else 1)
                if len(tracks) > track_len:
                    maxlength_msg = _(" {bad_tracks} tracks cannot be queued.").format(
                        bad_tracks=(len(tracks) - track_len)
                    )
                else:
                    maxlength_msg = ""
                songembed = discord.Embed(
                    title=_("Queued {num} track(s).{maxlength_msg}").format(
                        num=track_len, maxlength_msg=maxlength_msg
                    )
                )
                if (
                    not await self.config_cache.shuffle.get_context_value(ctx.guild)
                    and queue_dur > 0
                ):
                    if query.is_local and query.is_album:
                        footer = _("folder")
                    else:
                        footer = _("search")

                    songembed.set_footer(
                        text=_(
                            "{time} until start of {type} playback: starts at #{position} in queue"
                        ).format(
                            time=queue_total_duration,
                            position=before_queue_length + 1,
                            type=footer,
                        )
                    )
                return await self.send_embed_msg(ctx, embed=songembed)
            elif query.is_local and query.single_track:
                tracks = await self.get_localtrack_folder_list(ctx, query)
            elif query.is_local and query.is_album:
                if ctx.invoked_with == "folder":
                    return await self._local_play_all(ctx, query, from_search=True)
                else:
                    tracks = await self.get_localtrack_folder_list(ctx, query)
            else:
                try:
                    result, called_api = await self.api_interface.fetch_track(ctx, player, query)
                except TrackEnqueueError:
                    self.update_player_lock(ctx, False)
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable to Get Track"),
                        description=_(
                            "I'm unable to get a track from Lavalink at the moment, "
                            "try again in a few minutes."
                        ),
                    )
                except Exception as e:
                    self.update_player_lock(ctx, False)
                    raise e
                tracks = result.tracks
            if not tracks:
                embed = discord.Embed(title=_("Nothing found."))
                if (
                    await self.config_cache.external_lavalink_server.get_context_value(ctx.guild)
                    and query.is_local
                ):
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
                return await self.send_embed_msg(ctx, embed=embed)
        else:
            tracks = query

        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)

        len_search_pages = math.ceil(len(tracks) / 5)
        search_page_list = []
        async for page_num in AsyncIter(range(1, len_search_pages + 1)):
            embed = await self._build_search_page(ctx, tracks, page_num)
            search_page_list.append(embed)

        if dj_enabled and not can_skip:
            return await dpymenu(ctx, search_page_list)

        await menu(ctx, search_page_list, search_controls)

    @commands.command(name="playmix")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def command_playmix(self, ctx: commands.Context, *, query: str):
        """Generate and enqueue a mix playlist based on query."""
        query = Query.process_input(query, self.local_folder_current_path)
        restrict = await self.config_cache.url_restrict.get_context_value(ctx.guild)
        if restrict and self.match_url(str(query)):
            valid_url = self.is_url_allowed(str(query))
            if not valid_url:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("That URL is not allowed."),
                )
        elif not await self.is_query_allowed(self.config_cache, ctx, f"{query}", query_obj=query):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("That track is not allowed.")
            )
        can_skip = await self._can_instaskip(ctx, ctx.author)
        if await self.config_cache.dj_status.get_context_value(ctx.guild) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You need the DJ role to queue tracks."),
            )
        if not self._player_check(ctx):
            if self.lavalink_connection_aborted:
                msg = _("Connection to Lavalink has failed")
                desc = EmptyEmbed
                if await self.bot.is_owner(ctx.author):
                    desc = _("Please check your console or logs for details.")
                return await self.send_embed_msg(ctx, title=msg, description=desc)
            try:
                if not self.can_join_and_speak(ctx.author.voice.channel) or self.is_vc_full(
                    ctx.author.voice.channel
                ):
                    return await self.send_embed_msg(
                        ctx,
                        title=_("Unable To Play Tracks"),
                        description=_(
                            "I don't have permission to connect and speak in your channel."
                        ),
                    )
                await lavalink.connect(
                    ctx.author.voice.channel,
                    deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
                )
            except AttributeError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connect to a voice channel first."),
                )
            except IndexError:
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Play Tracks"),
                    description=_("Connection to Lavalink has not yet been established."),
                )
        player = lavalink.get_player(ctx.guild.id)
        player.store("notify_channel", ctx.channel.id)
        await self._eq_check(ctx, player)
        await self.set_player_settings(ctx)
        if (not ctx.author.voice or ctx.author.voice.channel != player.channel) and not can_skip:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("You must be in the voice channel to use the play command."),
            )
        if not query.valid:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Play Tracks"),
                description=_("No tracks found for `{query}`.").format(
                    query=query.to_string_user()
                ),
            )
        if len(player.queue) >= await self.config_cache.max_queue_size.get_context_value(
            player.guild
        ):
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=_("Queue size limit reached.")
            )
        if not query.single_track:
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Create Mixlist"),
                description=_("You need to specify a single track to generate a mixlist."),
            )
        elif not (query.is_youtube or query.is_spotify):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Create Mixlist"),
                description=_("You need to specify a YouTube or Spotify track."),
            )
        try:
            async with ctx.typing():
                if query.is_spotify:
                    tracks = await self._get_spotify_tracks(ctx, query)
                else:
                    tracks = await self._enqueue_tracks(ctx, query, enqueue=False)
                self.update_player_lock(ctx, False)
                if isinstance(tracks, discord.Message):
                    return
                if not tracks:
                    return await self.send_embed_msg(ctx, title=_("Couldn't generated a mixlist."))
                single_track = tracks if isinstance(tracks, lavalink.rest_api.Track) else tracks[0]
                _id = single_track._info["identifier"]
                mix = "https://www.youtube.com/watch?v={id}&list=RD{id}".format(id=_id)
                query = Query.process_input(mix, self.local_folder_current_path)
                if not await self.maybe_charge_requester(
                    ctx, await self.config_cache.jukebox_price.get_context_value(ctx.guild)
                ):
                    return
                await self._enqueue_tracks(ctx, query)
        except QueryUnauthorized as err:
            return await self.send_embed_msg(
                ctx, title=_("Unable To Play Tracks"), description=err.message
            )
        except Exception as e:
            self.update_player_lock(ctx, False)
            raise e
