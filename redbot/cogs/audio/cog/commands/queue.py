import asyncio
import contextlib
import datetime
import logging
from collections import MutableMapping

import discord
import lavalink
import math

from redbot.cogs.audio.cog import MixinMeta
from redbot.core import commands, checks
from redbot.core.utils.menus import (
    prev_page,
    close_menu,
    next_page,
    start_adding_reactions,
    menu,
    DEFAULT_CONTROLS,
)
from redbot.core.utils.predicates import ReactionPredicate

from ..utils import _
from ...utils import draw_time, get_track_description, userlimit

log = logging.getLogger("red.cogs.Audio.cog.commands.Queue")


class QueueCommands(MixinMeta):
    """
    All Queue commands.
    """

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def queue(self, ctx: commands.Context, *, page: int = 1):
        """List the songs in the queue."""

        async def _queue_menu(
            ctx: commands.Context,
            pages: list,
            controls: MutableMapping,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                await ctx.send_help(self.queue)
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                return None

        queue_controls = {
            "\N{LEFTWARDS BLACK ARROW}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}": next_page,
            "\N{INFORMATION SOURCE}": _queue_menu,
        }

        if not self._player_check(ctx):
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        player = lavalink.get_player(ctx.guild.id)

        if player.current and not player.queue:
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
            embed.set_footer(text=text)
            message = await self._embed_msg(ctx, embed=embed)
            dj_enabled = self._dj_status_cache.setdefault(
                ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
            )
            vote_enabled = await self.config.guild(ctx.guild).vote_enabled()
            if dj_enabled or vote_enabled:
                if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(
                    ctx
                ):
                    return

            expected = ("⏹", "⏯")
            emoji = {"stop": "⏹", "pause": "⏯"}
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
            if react == "stop":
                await self._clear_react(message, emoji)
                return await ctx.invoke(self.stop)
            elif react == "pause":
                await self._clear_react(message, emoji)
                return await ctx.invoke(self.pause)
            return
        elif not player.current and not player.queue:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))

        async with ctx.typing():
            limited_queue = player.queue[:500]  # TODO: Improve when Toby menu's are merged
            len_queue_pages = math.ceil(len(limited_queue) / 10)
            queue_page_list = []
            for page_num in range(1, len_queue_pages + 1):
                embed = await self._build_queue_page(ctx, limited_queue, player, page_num)
                queue_page_list.append(embed)
                await asyncio.sleep(0)
            if page > len_queue_pages:
                page = len_queue_pages
        return await menu(ctx, queue_page_list, queue_controls, page=(page - 1))

    @queue.command(name="clear")
    @commands.guild_only()
    async def _queue_clear(self, ctx: commands.Context):
        """Clears the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Clear Queue"),
                    description=_("You need the DJ role to clear the queue."),
                )
        player.queue.clear()
        await self._embed_msg(
            ctx, title=_("Queue Modified"), description=_("The queue has been cleared.")
        )

    @queue.command(name="clean")
    @commands.guild_only()
    async def _queue_clean(self, ctx: commands.Context):
        """Removes songs from the queue if the requester is not in the voice channel."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Clean Queue"),
                    description=_("You need the DJ role to clean the queue."),
                )
        clean_tracks = []
        removed_tracks = 0
        listeners = player.channel.members
        for track in player.queue:
            if track.requester in listeners:
                clean_tracks.append(track)
            else:
                removed_tracks += 1
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self._embed_msg(ctx, title=_("Removed 0 tracks."))
        else:
            await self._embed_msg(
                ctx,
                title=_("Removed racks from the queue"),
                description=_(
                    "Removed {removed_tracks} tracks queued by members "
                    "outside of the voice channel."
                ).format(removed_tracks=removed_tracks),
            )

    @queue.command(name="cleanself")
    @commands.guild_only()
    async def _queue_cleanself(self, ctx: commands.Context):
        """Removes all tracks you requested from the queue."""

        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))

        clean_tracks = []
        removed_tracks = 0
        for track in player.queue:
            if track.requester != ctx.author:
                clean_tracks.append(track)
            else:
                removed_tracks += 1
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self._embed_msg(ctx, title=_("Removed 0 tracks."))
        else:
            await self._embed_msg(
                ctx,
                title=_("Removed tracks from the queue"),
                description=_(
                    "Removed {removed_tracks} tracks queued by {member.display_name}."
                ).format(removed_tracks=removed_tracks, member=ctx.author),
            )

    @queue.command(name="search")
    @commands.guild_only()
    async def _queue_search(self, ctx: commands.Context, *, search_words: str):
        """Search the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))
        if not self._player_check(ctx) or not player.queue:
            return await self._embed_msg(ctx, title=_("There's nothing in the queue."))

        search_list = await self._build_queue_search_list(player.queue, search_words)
        if not search_list:
            return await self._embed_msg(ctx, title=_("No matches."))

        len_search_pages = math.ceil(len(search_list) / 10)
        search_page_list = []
        for page_num in range(1, len_search_pages + 1):
            embed = await self._build_queue_search_page(ctx, page_num, search_list)
            search_page_list.append(embed)
        await menu(ctx, search_page_list, DEFAULT_CONTROLS)

    @queue.command(name="shuffle")
    @commands.guild_only()
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def _queue_shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""
        dj_enabled = self._dj_status_cache.setdefault(
            ctx.guild.id, await self.config.guild(ctx.guild).dj_enabled()
        )
        if dj_enabled:
            if not await self._can_instaskip(ctx, ctx.author) and not await self._is_alone(ctx):
                ctx.command.reset_cooldown(ctx)
                return await self._embed_msg(
                    ctx,
                    title=_("Unable To Shuffle Queue"),
                    description=_("You need the DJ role to shuffle the queue."),
                )
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
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
                    title=_("Unable To Shuffle Queue"),
                    description=_("I don't have permission to connect to your channel."),
                )
            await lavalink.connect(ctx.author.voice.channel)
            player = lavalink.get_player(ctx.guild.id)
            player.store("connect", datetime.datetime.utcnow())
        except AttributeError:
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("Connect to a voice channel first."),
            )
        except IndexError:
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("Connection to Lavalink has not yet been established."),
            )
        except KeyError:
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
            )

        if not self._player_check(ctx) or not player.queue:
            ctx.command.reset_cooldown(ctx)
            return await self._embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
            )

        player.force_shuffle(0)
        return await self._embed_msg(ctx, title=_("Queue has been shuffled."))
