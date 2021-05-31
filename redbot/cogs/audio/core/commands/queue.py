import asyncio
import logging
from pathlib import Path
from typing import Optional

import discord
import lavalink
from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils._dpy_menus_utils import SimpleHybridMenu
from redbot.core.utils.menus import start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass
from ..utilities.menus.queue import QueueMenu, QueueSearchSource, QueueSource

log = logging.getLogger("red.cogs.Audio.cog.Commands.queue")
_ = Translator("Audio", Path(__file__))


class QueueCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.group(name="queue", invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_queue(self, ctx: commands.Context, *, page: int = 1):
        """List the songs in the queue."""

        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
        player = lavalink.get_player(ctx.guild.id)

        if player.current and not player.queue:
            arrow = await self.draw_time(ctx)
            pos = self.format_time(player.position)
            if player.current.is_stream:
                dur = "LIVE"
            else:
                dur = self.format_time(player.current.length)
            song = (
                await self.get_track_description(player.current, self.local_folder_current_path)
                or ""
            )
            song += _("\n Requested by: **{track.requester}**").format(track=player.current)
            song += f"\n\n{arrow}`{pos}`/`{dur}`"
            embed = discord.Embed(title=_("Now Playing"), description=song)
            thumbnail = await self.config_cache.thumbnail.get_context_value(ctx.guild)
            if thumbnail and player.current and player.current.thumbnail:
                embed.set_thumbnail(url=player.current.thumbnail)

            shuffle = await self.config_cache.shuffle.get_context_value(ctx.guild)
            repeat = await self.config_cache.repeat.get_context_value(ctx.guild)
            autoplay = await self.config_cache.autoplay.get_context_value(ctx.guild)
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
            message = await self.send_embed_msg(ctx, embed=embed)
            dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
            vote_enabled = await self.config_cache.votes.get_context_value(ctx.guild)
            if (
                (dj_enabled or vote_enabled)
                and not await self._can_instaskip(ctx, ctx.author)
                and not await self.is_requester_alone(ctx)
            ):
                return

            emoji = {
                "prev": "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                "stop": "\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}",
                "pause": "\N{BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                "next": "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
                "close": "\N{CROSS MARK}",
            }
            expected = tuple(emoji.values())
            if not player.queue and not autoplay:
                expected = (emoji["stop"], emoji["pause"], emoji["close"])
            if player.current:
                task: Optional[asyncio.Task] = start_adding_reactions(message, expected[:5])
            else:
                task: Optional[asyncio.Task] = None

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
                await ctx.invoke(self.command_prev)
            elif react == "stop":
                await self._clear_react(message, emoji)
                await ctx.invoke(self.command_stop)
            elif react == "pause":
                await self._clear_react(message, emoji)
                await ctx.invoke(self.command_pause)
            elif react == "next":
                await self._clear_react(message, emoji)
                await ctx.invoke(self.command_skip)
            elif react == "close":
                await message.delete()
            return
        elif not player.current and not player.queue:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))

        await QueueMenu(source=QueueSource(player.queue, self.config_cache), cog=self).start(
            ctx=ctx, wait=False, page=page
        )

    @command_queue.command(name="clear", aliases=["wipe", "reset"])
    async def command_queue_clear(self, ctx: commands.Context):
        """Clears the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
        if (
            dj_enabled
            and not await self._can_instaskip(ctx, ctx.author)
            and not await self.is_requester_alone(ctx)
        ):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Clear Queue"),
                description=_("You need the DJ role to clear the queue."),
            )
        async for track in AsyncIter(player.queue):
            await self.api_interface.persistent_queue_api.played(
                ctx.guild.id, track.extras.get("enqueue_time")
            )
        player.queue.clear()
        await self.send_embed_msg(
            ctx, title=_("Queue Modified"), description=_("The queue has been cleared.")
        )

    @command_queue.command(name="clean")
    async def command_queue_clean(self, ctx: commands.Context):
        """Removes songs from the queue if the requester is not in the voice channel."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
        if (
            dj_enabled
            and not await self._can_instaskip(ctx, ctx.author)
            and not await self.is_requester_alone(ctx)
        ):
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Clean Queue"),
                description=_("You need the DJ role to clean the queue."),
            )
        clean_tracks = []
        removed_tracks = 0
        listeners = player.channel.members
        async for track in AsyncIter(player.queue.copy()):
            if track.requester in listeners:
                clean_tracks.append(track)
            else:
                await self.api_interface.persistent_queue_api.played(
                    ctx.guild.id, track.extras.get("enqueue_time")
                )
                removed_tracks += 1
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self.send_embed_msg(ctx, title=_("Removed 0 tracks."))
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Removed Tracks From The Queue"),
                description=_(
                    "Removed {removed_tracks} tracks queued by members "
                    "outside of the voice channel."
                ).format(removed_tracks=removed_tracks),
            )

    @command_queue.command(name="cleanself")
    async def command_queue_cleanself(self, ctx: commands.Context):
        """Removes all tracks you requested from the queue."""

        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))

        clean_tracks = []
        removed_tracks = 0
        async for track in AsyncIter(player.queue.copy()):
            if track.requester != ctx.author:
                clean_tracks.append(track)
            else:
                removed_tracks += 1
                await self.api_interface.persistent_queue_api.played(
                    ctx.guild.id, track.extras.get("enqueue_time")
                )
        player.queue = clean_tracks
        if removed_tracks == 0:
            await self.send_embed_msg(ctx, title=_("Removed 0 tracks."))
        else:
            await self.send_embed_msg(
                ctx,
                title=_("Removed Tracks From The Queue"),
                description=_(
                    "Removed {removed_tracks} tracks queued by {member.display_name}."
                ).format(removed_tracks=removed_tracks, member=ctx.author),
            )

    @command_queue.command(name="search")
    async def command_queue_search(self, ctx: commands.Context, *, search_words: str):
        """Search the queue."""
        try:
            player = lavalink.get_player(ctx.guild.id)
        except KeyError:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))
        if not self._player_check(ctx) or not player.queue:
            return await self.send_embed_msg(ctx, title=_("There's nothing in the queue."))

        search_list = await self._build_queue_search_list(player.queue.copy(), search_words)
        if not search_list:
            return await self.send_embed_msg(ctx, title=_("No matches."))

        await SimpleHybridMenu(
            source=QueueSearchSource(search_list, self.config_cache), cog=self
        ).start(ctx=ctx, wait=False)

    @command_queue.command(name="shuffle")
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def command_queue_shuffle(self, ctx: commands.Context):
        """Shuffles the queue."""
        dj_enabled = await self.config_cache.dj_status.get_context_value(ctx.guild)
        if (
            dj_enabled
            and not await self._can_instaskip(ctx, ctx.author)
            and not await self.is_requester_alone(ctx)
        ):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("You need the DJ role to shuffle the queue."),
            )
        if not self._player_check(ctx):
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
            )
        try:
            vc = ctx.guild.me.voice.channel if ctx.guild.me.voice else ctx.author.voice.channel
            if not self.can_join_and_speak(vc) or self.is_vc_full(vc):
                ctx.command.reset_cooldown(ctx)
                return await self.send_embed_msg(
                    ctx,
                    title=_("Unable To Shuffle Queue"),
                    description=_("I don't have permission to connect and speak in your channel."),
                )
            player = await lavalink.connect(
                vc,
                deafen=await self.config_cache.auto_deafen.get_context_value(ctx.guild),
            )
            player.store("notify_channel", ctx.channel.id)
        except AttributeError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("Connect to a voice channel first."),
            )
        except IndexError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("Connection to Lavalink has not yet been established."),
            )
        except KeyError:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
            )

        if not self._player_check(ctx) or not player.queue:
            ctx.command.reset_cooldown(ctx)
            return await self.send_embed_msg(
                ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
            )

        player.force_shuffle(0)
        return await self.send_embed_msg(ctx, title=_("Queue has been shuffled."))
