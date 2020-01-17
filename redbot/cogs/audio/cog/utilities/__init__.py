import asyncio
import contextlib
import datetime
import logging
import time
from pathlib import Path
from typing import List, MutableMapping, Optional, Union

import discord
import lavalink
import math
from discord.embeds import EmptyEmbed
from fuzzywuzzy import process

from redbot.cogs.audio.audio_dataclasses import LocalPath, Query
from redbot.cogs.audio.audio_logging import IS_DEBUG
from redbot.cogs.audio.cog.utilities.player import PlayerUtilities
from redbot.cogs.audio.cog.utilities.playlists import PlaylistUtilities
from redbot.cogs.audio.cog.utilities.staticmethod import StaticMethodUtilities
from redbot.cogs.audio.cog.utils import CompositeMetaClass, _
from redbot.cogs.audio.equalizer import Equalizer
from redbot.core import bank, commands
from redbot.core.utils.chat_formatting import bold, box, humanize_number

log = logging.getLogger("red.cogs.Audio.cog.utilities")


class Utilities(
    StaticMethodUtilities, PlayerUtilities, PlaylistUtilities, metaclass=CompositeMetaClass
):
    def format_playlist_picker_data(self, pid, pname, ptracks, pauthor, scope) -> str:
        author = self.bot.get_user(pauthor) or pauthor or _("Unknown")
        line = _(
            " - Name:   <{pname}>\n"
            " - Scope:  < {scope} >\n"
            " - ID:     < {pid} >\n"
            " - Tracks: < {ptracks} >\n"
            " - Author: < {author} >\n\n"
        ).format(
            pname=pname, scope=self.humanize_scope(scope), pid=pid, ptracks=ptracks, author=author
        )
        return box(line, lang="md")

    async def clear_react(self, message: discord.Message, emoji: MutableMapping = None) -> None:
        try:
            await message.clear_reactions()
        except discord.Forbidden:
            if not emoji:
                return
            with contextlib.suppress(discord.HTTPException):
                for key in emoji.values():
                    await asyncio.sleep(0.2)
                    await message.remove_reaction(key, self.bot.user)
        except discord.HTTPException:
            return

    def track_creator(self, player, position=None, other_track=None) -> MutableMapping:
        if position == "np":
            queued_track = player.current
        elif position is None:
            queued_track = other_track
        else:
            queued_track = player.queue[position]
        return self.track_to_json(queued_track)

    def rsetattr(self, obj, attr, val):
        pre, _, post = attr.rpartition(".")
        return setattr(self.rgetattr(obj, pre) if pre else obj, post, val)

    async def error_reset(self, player: lavalink.Player):
        guild = self.rgetattr(player, "channel.guild.id", None)
        if not guild:
            return
        now = time.time()
        seconds_allowed = 10
        last_error = self._error_timer.setdefault(guild, now)
        if now - seconds_allowed > last_error:
            self._error_timer[guild] = 0
            self._error_counter[guild] = 0

    async def increase_error_counter(self, player: lavalink.Player) -> bool:
        guild = self.rgetattr(player, "channel.guild.id", None)
        if not guild:
            return False
        now = time.time()
        self._error_counter[guild] += 1
        self._error_timer[guild] = now
        return self._error_counter[guild] >= 5

    async def _localtracks_folders(
        self, ctx: commands.Context, search_subfolders=False
    ) -> Optional[List[Union[Path, LocalPath]]]:
        audio_data = LocalPath(LocalPath(None).localtrack_folder.absolute())
        if not await self._localtracks_check(ctx):
            return

        return (
            await audio_data.subfolders_in_tree()
            if search_subfolders
            else await audio_data.subfolders()
        )

    async def _folder_list(self, ctx: commands.Context, query: Query) -> Optional[List[Query]]:
        if not await self._localtracks_check(ctx):
            return
        query = Query.process_input(query)
        if not query.track.exists():
            return
        return (
            await query.track.tracks_in_tree()
            if query.search_subfolders
            else await query.track.tracks_in_folder()
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
            await query.track.tracks_in_tree()
            if query.search_subfolders
            else await query.track.tracks_in_folder()
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
            arrow = await self.draw_time(ctx)
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
        queue_dur = await self.queue_duration(ctx)
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
            description = self.get_track_description(search_choice)
        else:
            search_choice = Query.process_input(search_choice)
            if search_choice.track.exists() and search_choice.track.is_dir():
                return await ctx.invoke(self.search, query=search_choice)
            elif search_choice.track.exists() and search_choice.track.is_file():
                search_choice.invoked_from = "localtrack"
            return await ctx.invoke(self.play, query=search_choice)

        songembed = discord.Embed(title=_("Track Enqueued"), description=description)
        queue_dur = await self.queue_duration(ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        before_queue_length = len(player.queue)

        if not await self.is_allowed(
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

            if self.track_limit(search_choice.length, guild_data["maxlength"]):
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

    async def _clear_react(self, message: discord.Message, emoji: MutableMapping = None):
        """Non blocking version of clear_react."""
        return self.bot.loop.create_task(self.clear_react(message, emoji))

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
            await self.remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, eq, message, max(selected - 1, 0))

        if react_emoji == "\N{BLACK RIGHTWARDS ARROW}":
            await self.remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, eq, message, min(selected + 1, 14))

        if react_emoji == "\N{UP-POINTING SMALL RED TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _max = "{:.2f}".format(min(eq.get_gain(selected) + 0.1, 1.0))
            eq.set_gain(selected, float(_max))
            await self._apply_gain(ctx.guild.id, selected, _max)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{DOWN-POINTING SMALL RED TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _min = "{:.2f}".format(max(eq.get_gain(selected) - 0.1, -0.25))
            eq.set_gain(selected, float(_min))
            await self._apply_gain(ctx.guild.id, selected, _min)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK UP-POINTING DOUBLE TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _max = 1.0
            eq.set_gain(selected, _max)
            await self._apply_gain(ctx.guild.id, selected, _max)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _min = -0.25
            eq.set_gain(selected, _min)
            await self._apply_gain(ctx.guild.id, selected, _min)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK LEFT-POINTING TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            selected = 0
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            selected = 14
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{BLACK CIRCLE FOR RECORD}":
            await self.remove_react(message, react_emoji, react_user)
            for band in range(eq._band_count):
                eq.set_gain(band, 0.0)
            await self._apply_gains(ctx.guild.id, eq.bands)
            await self._eq_interact(ctx, player, eq, message, selected)

        if react_emoji == "\N{INFORMATION SOURCE}":
            await self.remove_react(message, react_emoji, react_user)
            await ctx.send_help(self.eq)
            await self._eq_interact(ctx, player, eq, message, selected)

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

    async def _process_db(self, ctx: commands.Context):
        await self.api_interface.run_tasks(ctx)

    async def _close_database(self):
        await self.api_interface.run_all_pending_tasks()
        self.api_interface.close()

    async def _build_queue_search_list(self, queue_list, search_words):
        track_list = []
        queue_idx = 0
        for i, track in enumerate(queue_list, start=1):
            if i % 100 == 0:  # TODO: Improve when Toby menu's are merged
                await asyncio.sleep(0.1)
            queue_idx = queue_idx + 1
            if not self.match_url(track.uri):
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

    async def _build_queue_search_page(self, ctx: commands.Context, page_num, search_list):
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
                page_num=self.humanize_number(page_num),
                total_pages=self.humanize_number(search_num_pages),
                num_tracks=len(search_list),
            )
        )
        return embed

    def _format_search_options(self, search_choice):
        query = Query.process_input(search_choice)
        description = self.get_track_description(search_choice)
        return description, query
