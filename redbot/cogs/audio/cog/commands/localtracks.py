import contextlib
import logging
from typing import Optional, MutableMapping

import discord
import math

from redbot.cogs.audio.cog import MixinMeta
from redbot.core import commands, checks
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu, prev_page, close_menu, next_page

from ..utils import _
from ...audio_dataclasses import LocalPath, Query

log = logging.getLogger("red.cogs.Audio.cog.commands.LocalTracks")


class LocalTracksCommands(MixinMeta):
    """
    All Local Track commands.
    """

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def local(self, ctx: commands.Context):
        """Local playback commands."""

    @local.command(name="folder", aliases=["start"])
    async def local_folder(
        self, ctx: commands.Context, play_subfolders: Optional[bool] = True, *, folder: str = None
    ):
        """Play all songs in a localtracks folder."""
        if not await self._localtracks_check(ctx):
            return

        if not folder:
            await ctx.invoke(self.local_play, play_subfolders=play_subfolders)
        else:
            folder = folder.strip()
            _dir = LocalPath.joinpath(folder)
            if not _dir.exists():
                return await self._embed_msg(
                    ctx,
                    title=_("Folder Not Found"),
                    description=_("Localtracks folder named {name} does not exist.").format(
                        name=folder
                    ),
                )
            query = Query.process_input(_dir, search_subfolders=play_subfolders)
            await self._local_play_all(ctx, query, from_search=False if not folder else True)

    @local.command(name="play")
    async def local_play(self, ctx: commands.Context, play_subfolders: Optional[bool] = True):
        """Play a local track."""
        if not await self._localtracks_check(ctx):
            return
        localtracks_folders = await self._localtracks_folders(
            ctx, search_subfolders=play_subfolders
        )
        if not localtracks_folders:
            return await self._embed_msg(ctx, title=_("No album folders found."))
        async with ctx.typing():
            len_folder_pages = math.ceil(len(localtracks_folders) / 5)
            folder_page_list = []
            for page_num in range(1, len_folder_pages + 1):
                embed = await self._build_search_page(ctx, localtracks_folders, page_num)
                folder_page_list.append(embed)

        async def _local_folder_menu(
            ctx: commands.Context,
            pages: list,
            controls: MutableMapping,
            message: discord.Message,
            page: int,
            timeout: float,
            emoji: str,
        ):
            if message:
                with contextlib.suppress(discord.HTTPException):
                    await message.delete()
                await self._search_button_action(ctx, localtracks_folders, emoji, page)
                return None

        local_folder_controls = {
            "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}": _local_folder_menu,
            "\N{LEFTWARDS BLACK ARROW}": prev_page,
            "\N{CROSS MARK}": close_menu,
            "\N{BLACK RIGHTWARDS ARROW}": next_page,
        }

        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if dj_enabled and not await self._can_instaskip(ctx, ctx.author):
            return await menu(ctx, folder_page_list, DEFAULT_CONTROLS)
        else:
            await menu(ctx, folder_page_list, local_folder_controls)

    @local.command(name="search")
    async def local_search(
        self, ctx: commands.Context, search_subfolders: Optional[bool] = True, *, search_words
    ):
        """Search for songs across all localtracks folders."""
        if not await self._localtracks_check(ctx):
            return
        all_tracks = await self._folder_list(
            ctx,
            (
                Query.process_input(
                    LocalPath(await self.config.localpath()).localtrack_folder.absolute(),
                    search_subfolders=search_subfolders,
                )
            ),
        )
        if not all_tracks:
            return await self._embed_msg(ctx, title=_("No album folders found."))
        async with ctx.typing():
            search_list = await self._build_local_search_list(all_tracks, search_words)
        if not search_list:
            return await self._embed_msg(ctx, title=_("No matches."))
        return await ctx.invoke(self.search, query=search_list)
