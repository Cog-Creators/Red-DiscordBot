import queue
from datetime import timedelta
from typing import List, Tuple

import discord
import lavalink

from redbot.cogs.audio.audio_dataclasses import LocalPath, Query
from redbot.cogs.audio.core.utilities import SettingCacheManager
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils._dpy_menus_utils import HybridMenu, SimpleHybridMenu
from redbot.core.utils.antispam import AntiSpam
from redbot.core.utils.chat_formatting import humanize_number
from redbot.vendored.discord.ext import menus
from redbot.vendored.discord.ext.menus import Last, button

_ = Translator("Audio", __file__)


class QueueSource(menus.ListPageSource):
    def __init__(self, entries: List[lavalink.Track], cache: SettingCacheManager):
        super().__init__(entries, per_page=15)
        self.config_cache = cache

    async def format_page(
        self, menu: SimpleHybridMenu, entries: List[lavalink.Track]
    ) -> discord.Embed:

        shuffle = await self.config_cache.shuffle.get_context_value(menu.ctx.guild)
        repeat = await self.config_cache.repeat.get_context_value(menu.ctx.guild)
        autoplay = await self.config_cache.autoplay.get_context_value(menu.ctx.guild)
        player = lavalink.get_player(menu.ctx.guild.id)
        page_num = menu.current_page + 1
        queue_num_pages = self.get_max_pages()
        queue_idx_start = (page_num - 1) * self.per_page
        queue_list = ""

        arrow = await menu.ctx.cog.draw_time(menu.ctx)
        pos = menu.ctx.cog.format_time(player.position)

        if player.current.is_stream:
            dur = "LIVE"
        else:
            dur = menu.ctx.cog.format_time(player.current.length)

        query = Query.process_input(player.current, menu.ctx.cog.local_folder_current_path)
        current_track_description = await menu.ctx.cog.get_track_description(
            player.current, menu.ctx.cog.local_folder_current_path
        )
        if query.is_stream:
            queue_list += _("**Currently livestreaming:**\n")
            queue_list += f"{current_track_description}\n"
            queue_list += _("Requester: **{user}**").format(user=player.current.requester.mention)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"
        else:
            queue_list += _("Playing: ")
            queue_list += f"{current_track_description}\n"
            queue_list += _("Requester: **{user}**").format(user=player.current.requester.mention)
            queue_list += f"\n\n{arrow}`{pos}`/`{dur}`\n\n"

        async for i, track in AsyncIter(entries).enumerate(start=queue_idx_start):
            track_idx = i + 1
            track_description = await menu.ctx.cog.get_track_description(
                track, menu.ctx.cog.local_folder_current_path, shorten=True
            )
            queue_list += f"`{track_idx}.` {track_description}\n"

        embed = discord.Embed(
            colour=await menu.ctx.embed_colour(),
            title=_("Queue for __{guild_name}__").format(guild_name=menu.ctx.guild.name),
            description=queue_list,
        )

        if (
            await self.config_cache.thumbnail.get_context_value(menu.ctx.guild)
            and player.current.thumbnail
        ):
            embed.set_thumbnail(url=player.current.thumbnail)
        queue_dur = await menu.ctx.cog.queue_duration(menu.ctx)
        queue_total_duration = menu.ctx.cog.format_time(queue_dur)
        text = _(
            "Page {page_num}/{total_pages} | {num_tracks} tracks | {num_remaining} remaining\n"
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


class QueueSearchSource(menus.ListPageSource):
    def __init__(self, entries: List[lavalink.Track], cache: SettingCacheManager):
        super().__init__(entries, per_page=15)
        self.config_cache = cache

    async def format_page(
        self, menu: SimpleHybridMenu, entries: List[Tuple[int, str]]
    ) -> discord.Embed:
        page_num = menu.current_page + 1
        search_num_pages = self.get_max_pages()
        search_idx_start = (page_num - 1) * self.per_page
        track_match = ""
        async for i, track in AsyncIter(entries).enumerate(start=search_idx_start):
            track_idx = i + 1
            if type(track) is str:
                track_location = LocalPath(
                    track, menu.ctx.cog.local_folder_current_path
                ).to_string_user()
                track_match += "`{}.` **{}**\n".format(track_idx, track_location)
            else:
                track_match += "`{}.` **{}**\n".format(track[0], track[1])
        embed = discord.Embed(
            colour=await menu.ctx.embed_colour(),
            title=_("Matching Tracks:"),
            description=track_match,
        )
        embed.set_footer(
            text=_("Page {page_num}/{total_pages} | {num_tracks} tracks").format(
                page_num=humanize_number(page_num),
                total_pages=humanize_number(search_num_pages),
                num_tracks=len(self.entries),
            )
        )


class QueueMenu(HybridMenu, inherit_buttons=True):
    def __init__(self, *args, **kwargs):
        super(QueueMenu, self).__init__(*args, **kwargs)
        self._antispam = {}

    async def _shuffle(self):
        self._antispam[self.ctx.guild.id][self.ctx.author.id].stamp()

        dj_enabled = await self.ctx.cog.config_cache.dj_status.get_context_value(self.ctx.guild)
        if (
            dj_enabled
            and not await self.ctx.cog._can_instaskip(self.ctx, self.ctx.author)
            and not await self.ctx.cog.is_requester_alone(self.ctx)
        ):
            self.ctx.command.reset_cooldown(self.ctx)
            return await self.ctx.cog.send_embed_msg(
                self.ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("You need the DJ role to shuffle the queue."),
                delete_after=10,
            )
        if not self.ctx.cog._player_check(self.ctx):
            self.ctx.command.reset_cooldown(self.ctx)
            return await self.ctx.cog.send_embed_msg(
                self.ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
                delete_after=10,
            )
        try:
            player = lavalink.get_player(self.ctx.guild.id)
        except KeyError:
            self.ctx.command.reset_cooldown(self.ctx)
            return await self.ctx.cog.send_embed_msg(
                self.ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
                delete_after=10,
            )

        if not self.ctx.cog._player_check(self.ctx) or not player.queue:
            self.ctx.command.reset_cooldown(self.ctx)
            return await self.ctx.cog.send_embed_msg(
                self.ctx,
                title=_("Unable To Shuffle Queue"),
                description=_("There's nothing in the queue."),
                delete_after=10,
            )

        player.force_shuffle(0)
        return await self.ctx.cog.send_embed_msg(
            self.ctx, title=_("Queue has been shuffled."), delete_after=5
        )

    def _skip_has_external_permission(self):
        return self._has_external_emojis_perms()

    def _skip_missing_external_permission(self):
        return self._has_not_external_emojis_perm()

    @button(
        "\N{TWISTED RIGHTWARDS ARROWS}",
        skip_if=_skip_has_external_permission,
        position=Last(3),
    )
    async def go_to_shuffle(self, payload):
        if self.ctx.guild.id not in self._antispam:
            self._antispam[self.ctx.guild.id] = {}
        if self.ctx.author.id not in self._antispam[self.ctx.guild.id]:
            self._antispam[self.ctx.guild.id][self.ctx.author.id] = AntiSpam(
                [
                    (timedelta(seconds=10), 1),
                ]
            )
        if self._antispam[self.ctx.guild.id][self.ctx.author.id].spammy:
            return
        await self._shuffle()
        await self.show_checked_page(self.current_page)

    @button(
        "\N{TWISTED RIGHTWARDS ARROWS}",
        skip_if=_skip_missing_external_permission,
        position=Last(3),
    )
    async def go_to_shuffle_custom(self, payload):
        if self.ctx.guild.id not in self._antispam:
            self._antispam[self.ctx.guild.id] = {}
        if self.ctx.author.id not in self._antispam[self.ctx.guild.id]:
            self._antispam[self.ctx.guild.id][self.ctx.author.id] = AntiSpam(
                [
                    (timedelta(seconds=10), 1),
                ]
            )
        if self._antispam[self.ctx.guild.id][self.ctx.author.id].spammy:
            return
        await self._shuffle()
        await self.show_checked_page(self.current_page)

    @button(
        "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}",
        skip_if=_skip_has_external_permission,
        position=Last(4),
    )
    async def go_to_info(self, payload):
        self.stop()
        await self.ctx.send_help(self.ctx.cog.command_queue)

    @button(
        "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}",
        skip_if=_skip_missing_external_permission,
        position=Last(4),
    )
    async def go_to_info_custom(self, payload):
        self.stop()
        await self.ctx.send_help(self.ctx.cog.command_queue)
