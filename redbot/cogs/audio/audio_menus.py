from typing import List, Tuple, Dict, Any, Optional
import os
import discord
import lavalink
import math

from redbot.cogs.audio import dataclasses

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.i18n import Translator
from redbot.core.utils import chat_formatting as chatutils
from redbot.core.utils.chat_formatting import bold
from redbot.core.utils.menus import PagedMenu

_ = Translator("Audio", __file__)
_config = None
_bot = None


def _pass_config_to_menus(config: Config, bot: Red):
    global _config, _bot
    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot

from redbot.cogs.audio.utils import draw_time, queue_duration


class QueueMenu(PagedMenu, exit_button=True, initial_emojis=("⬅", "❌", "➡", "ℹ")):
    def __init__(self, *, player, queue_cms, **kwargs) -> None:
        self._player = player
        self._queue = player.queue or []
        self._queue_cmd = queue_cms
        self._cur_song = 0
        self._queue_length = len(self._queue)
        super().__init__(pages=[], arrows_always=True, **kwargs)

    async def _before_send(self, **kwargs) -> None:
        if not self._pages:
            self._pages = [await self._format_page()]
        if self._queue_length < 10:
            # Only one page, no need for arrows
            self._initial_emojis = ("❌", "ℹ")

    @PagedMenu.handler("ℹ")
    async def _queue_help(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
        await self.ctx.send_help(self._queue_cmd)
        await self.ctx.message.delete()

    @PagedMenu.handler("⬅")
    async def prev_page(self, payload: Optional[discord.RawReactionActionEvent] = None) -> None:
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
        if self._queue_length < 10:
            return
        if self._cur_song > self._queue_length - 10:
            self._cur_song = 0
        else:
            self._cur_song += 10

        if self._cur_page == len(self._pages) - 1:
            self._pages.append(await self._format_page())

        await super().next_page(payload=payload)

    async def _format_page(self) -> str:
        songs = self._queue[self._cur_song : self._cur_song + 10]

        shuffle = await _config.guild(self.ctx.guild).shuffle()
        repeat = await _config.guild(self.ctx.guild).repeat()
        autoplay = await _config.guild(self.ctx.guild).auto_play()

        queue_num_pages = math.ceil(self._queue_length / 10)
        queue_list = ""
        arrow = await draw_time(self.ctx)
        pos = lavalink.utils.format_time(self._player.position)

        if self._player.current.is_stream:
            dur = "LIVE"
        else:
            dur = lavalink.utils.format_time(self._player.current.length)

        if self._player.current.is_stream:
            queue_list += _("**Currently livestreaming:**\n")

        elif any(
                x in self._player.current.uri for x in [f"{os.sep}localtracks", f"localtracks{os.sep}"]
        ):
            if self._player.current.title != "Unknown title":
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + "**{current.author} - {current.title}**".format(current=self._player.current),
                        dataclasses.LocalPath(self._player.current.uri).to_string_hidden(),
                        _("Requested by: **{user}**\n").format(user=self._player.current.requester),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
            else:
                queue_list += "\n".join(
                    (
                        _("Playing: ")
                        + dataclasses.LocalPath(self._player.current.uri).to_string_hidden(),
                        _("Requested by: **{user}**\n").format(user=self._player.current.requester),
                        f"{arrow}`{pos}`/`{dur}`\n\n",
                    )
                )
        else:
            queue_list += _("Playing: ")
            queue_list += "**[{current.title}]({current.uri})**\n".format(current=self._player.current)
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
            cur_page=self._cur_page + 1,
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

