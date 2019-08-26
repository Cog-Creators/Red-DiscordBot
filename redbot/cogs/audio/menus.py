# -*- coding: utf-8 -*-
import contextlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
import lavalink
import math

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import bold
from redbot.core.utils.menus import PagedMenu
from . import dataclasses
from .utils import draw_time, queue_duration

_ = Translator("Audio", __file__)
_config = None
_bot = None


def _pass_config_to_menus(config: Config, bot: Red):
    global _config, _bot
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot


class QueueMenu(PagedMenu, exit_button=True, initial_emojis=("⬅", "❌", "➡", "🔀", "🔃", "ℹ")):
    def __init__(self, *, player, audio_cog, timeout=None, first_page=0, **kwargs) -> None:
        now = datetime.now(tz=timezone.utc) - timedelta(seconds=60)
        self._shuffle_timer = now
        self._refresh_timer = now
        self._refresh_msg = None
        self._shuffle_msg = None
        self._player = player
        self._queue = player.queue or []
        self._audio_cog = audio_cog
        self._queue_cmd = self._audio_cog.queue
        self._queue_length = len(self._queue)
        self._cur_song = 10 * max(first_page - 1, 0)
        if self._cur_song > self._queue_length:
            self._cur_song = 0
        super().__init__(pages=[], arrows_always=True, timeout=timeout, **kwargs)

    async def _before_send(self, **kwargs) -> None:
        if not self._pages:
            self._pages = [await self._format_page()]
        if self._queue_length < 10:
            # Only one page, no need for arrows
            self._initial_emojis = ("❌", "🔀", "🔃", "ℹ")

    @PagedMenu.handler("ℹ")
    async def _queue_help(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        await self.ctx.send_help(self._queue_cmd)
        await self.exit_menu(payload=payload)

    # noinspection PyUnusedLocal
    @PagedMenu.handler("🔃")
    async def _queue_refresh(
        self, payload: Optional[discord.RawReactionActionEvent] = None
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        if self._refresh_timer + timedelta(seconds=5) > now:
            if self._refresh_msg is None:
                self._refresh_msg = await self.ctx.maybe_send_embed(
                    _("There's a 5 second cooldown on queue refresh.")
                )
            return
        self._player = lavalink.get_player(self.ctx.guild.id)
        self._queue = self._player.queue or []
        self._queue_length = len(self._queue)
        self._cur_page = 0
        self._pages = [await self._format_page()]
        self._refresh_timer = now
        if self._refresh_msg is not None:
            with contextlib.suppress(discord.HTTPException):
                await self._refresh_msg.delete()
            self._refresh_msg = None
        await super()._update_message()

    # noinspection PyUnusedLocal
    @PagedMenu.handler("🔀")
    async def _queue_shuffle(
        self, payload: Optional[discord.RawReactionActionEvent] = None
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        if self._shuffle_timer + timedelta(seconds=30) > now:
            if self._shuffle_msg is None:
                self._shuffle_msg = await self.ctx.maybe_send_embed(
                    _("There's a 30 second cooldown on queue shuffle.")
                )
            return
        # noinspection PyProtectedMember
        await self.ctx.invoke(self._audio_cog._queue_shuffle)
        self._player = lavalink.get_player(self.ctx.guild.id)
        self._queue = self._player.queue or []
        self._queue_length = len(self._queue)
        self._cur_page = 0
        self._pages = [await self._format_page()]
        self._shuffle_timer = now
        if self._shuffle_msg is not None:
            with contextlib.suppress(discord.HTTPException):
                await self._shuffle_msg.delete()
            self._shuffle_msg = None
        await super()._update_message()

    @PagedMenu.handler("⬅")
    async def prev_page(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        self._player = lavalink.get_player(self.ctx.guild.id)
        self._queue = self._player.queue or []
        self._queue_length = len(self._queue)
        if self._queue_length < 10:
            return
        if self._cur_song == 0:
            self._cur_song = self._queue_length - self._queue_length % 10
            if self._cur_song == self._queue_length:
                self._cur_song -= 10
        else:
            self._cur_song -= 10

        if self._cur_page == 0:
            self._cur_page = 1
            self._pages.insert(0, await self._format_page())

        await super().prev_page(payload=payload)

    @PagedMenu.handler("➡")
    async def next_page(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        self._player = lavalink.get_player(self.ctx.guild.id)
        self._queue = self._player.queue or []
        self._queue_length = len(self._queue)
        if self._queue_length < 10:
            return
        if self._cur_song > self._queue_length - 10:
            self._cur_song = 0
        else:
            self._cur_song += 10

        if self._cur_page == len(self._pages) - 1:
            self._pages.append(await self._format_page())

        await super().next_page(payload=payload)

    async def _format_page(self) -> discord.Embed:
        # noinspection PyPep8
        songs = self._queue[self._cur_song : self._cur_song + 10]

        shuffle = await _config.guild(self.ctx.guild).shuffle()
        repeat = await _config.guild(self.ctx.guild).repeat()
        autoplay = await _config.guild(self.ctx.guild).auto_play()

        queue_num_pages = math.ceil(self._queue_length / 10)
        page = math.ceil(self._cur_song / 10) + 1
        queue_list = ""
        arrow = await draw_time(self.ctx)
        pos = lavalink.utils.format_time(self._player.position)

        if self._player.current.is_stream:
            dur = "LIVE"
        else:
            dur = lavalink.utils.format_time(self._player.current.length)

        if self._player.current.is_stream:
            queue_list += _("**Currently livestreaming:**\n")
            queue_list += "**[{current.title}]({current.uri})**\n".format(
                current=self._player.current
            )
            queue_list += _("Requested by: **{user}**").format(user=self._player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        elif any(
            x in self._player.current.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
        ):
            if self._player.current.title != "Unknown title":
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + "**{current.author} - {current.title}**".format(
                            current=self._player.current
                        ),
                        dataclasses.LocalPath(self._player.current.uri).to_string_hidden(),
                        _("Requested by: **{user}**\n").format(
                            user=self._player.current.requester
                        ),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
            else:
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + dataclasses.LocalPath(self._player.current.uri).to_string_hidden(),
                        _("Requested by: **{user}**\n").format(
                            user=self._player.current.requester
                        ),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
        else:
            queue_list += _("Playing: ")
            queue_list += "**[{current.title}]({current.uri})**\n".format(
                current=self._player.current
            )
            queue_list += _("Requested by: **{user}**").format(user=self._player.current.requester)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        for i, track in enumerate(songs, start=self._cur_song):

            if len(track.title) > 40:
                track_title = str(track.title).replace("[", "")
                track_title = "{}...".format((track_title[:40]).rstrip(" "))
            else:
                track_title = track.title
            req_user = track.requester
            track_idx = i + 1
            if any(x in track.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]):
                if track.title == "Unknown title":
                    queue_list += f"`{track_idx}.` " + ", ".join(
                        (
                            bold(dataclasses.LocalPath(track.uri).to_string_hidden()),
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

        embed = discord.Embed(
            colour=await self.ctx.embed_colour(),
            title="Queue for " + self.ctx.guild.name,
            description=queue_list,
        )
        if await _config.guild(self.ctx.guild).thumbnail() and self._player.current.thumbnail:
            embed.set_thumbnail(url=self._player.current.thumbnail)
        queue_dur = await queue_duration(self.ctx)
        queue_total_duration = lavalink.utils.format_time(queue_dur)
        text = _(
            "Page {cur_page}/{total_pages} | {num_tracks} "
            "tracks, {num_remaining} remaining  |  \n\n"
        ).format(
            cur_page=page,
            total_pages=queue_num_pages,
            num_tracks=self._queue_length,
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


class PlayListChangesMenu(
    PagedMenu, exit_button=True, initial_emojis=("⬅", "❌", "➡", "➕", "➖", "ℹ")
):
    def __init__(
        self,
        *,
        added,
        removed,
        info_command,
        scope,
        author,
        guild,
        specified_user,
        playlist_matches,
        timeout=None,
        **kwargs,
    ) -> None:
        self._added_pages = added
        self._removed_pages = removed
        self._info_command = info_command
        self._playlist_matches = playlist_matches
        self._scope = scope
        self._playlist_author = author
        self._playlist_guild = guild
        self._specified_user = specified_user

        super().__init__(pages=[], arrows_always=True, timeout=timeout, **kwargs)

    async def _before_send(self, **kwargs) -> None:
        if not self._pages and self._removed_pages:
            self._focus_pages = self._removed_pages
        elif not self._pages and self._added_pages:
            self._focus_pages = self._added_pages
        self._pages = self._focus_pages

    @PagedMenu.handler("ℹ")
    async def _playlist_info(
        self, payload: Optional[discord.RawReactionActionEvent] = None
    ) -> None:
        await self.exit_menu(payload=payload)
        await self.ctx.invoke(
            self._info_command,
            playlist_matches=self._playlist_matches,
            scope_data=(
                self._scope,
                self._playlist_author,
                self._playlist_guild,
                self._specified_user,
            ),
        )

    # noinspection PyUnusedLocal
    @PagedMenu.handler("➖")
    async def _playlist_removed(
        self, payload: Optional[discord.RawReactionActionEvent] = None
    ) -> None:
        if not self._removed_pages:
            return
        self._focus_pages = self._removed_pages
        self._cur_page = 0
        self._pages = self._focus_pages
        await super()._update_message()

    # noinspection PyUnusedLocal
    @PagedMenu.handler("➕")
    async def _playlist_added(
        self, payload: Optional[discord.RawReactionActionEvent] = None
    ) -> None:
        if not self._added_pages:
            return
        self._focus_pages = self._added_pages
        self._pages = self._focus_pages
        self._cur_page = 0
        await super()._update_message()
