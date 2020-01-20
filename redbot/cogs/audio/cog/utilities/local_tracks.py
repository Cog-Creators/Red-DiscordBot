import asyncio
import contextlib
import logging
from pathlib import Path
from typing import List, Union

import lavalink
from fuzzywuzzy import process

from redbot.core import commands
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass, _
from ...audio_dataclasses import LocalPath, Query

log = logging.getLogger("red.cogs.Audio.cog.Utilities.local_tracks")


class LocalTrackUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def get_localtracks_folders(
        self, ctx: commands.Context, search_subfolders=False
    ) -> List[Union[Path, LocalPath]]:
        audio_data = LocalPath(None, self.local_folder_current_path).localtrack_folder.absolute()
        if not await self.has_localtracks_check(ctx):
            return []

        return (
            await audio_data.subfolders_in_tree()
            if search_subfolders
            else await audio_data.subfolders()
        )

    async def get_localtrack_folder_list(self, ctx: commands.Context, query: Query) -> List[Query]:
        """Return a list of folders per the provided query"""
        if not await self.has_localtracks_check(ctx):
            return []
        query = Query.process_input(query, self.local_folder_current_path)
        if not query.is_local:
            return []
        if not query.local_track_path.exists():
            return []
        return (
            await query.local_track_path.tracks_in_tree()
            if query.search_subfolders
            else await query.local_track_path.tracks_in_folder()
        )

    async def get_localtrack_folder_tracks(
        self, ctx, player: lavalink.player_manager.Player, query: Query
    ) -> List[lavalink.rest_api.Track]:
        """Return a list of tracks per the provided query"""
        if not await self.has_localtracks_check(ctx):
            return []

        audio_data = LocalPath(None, self.local_folder_current_path)
        try:
            query.local_track_path.path.relative_to(audio_data.to_string())
        except ValueError:
            return []
        local_tracks = []
        for local_file in await self.get_all_localtrack_folder_tracks(ctx, query):
            trackdata, called_api = await self.api_interface.fetch_track(ctx, player, local_file)
            with contextlib.suppress(IndexError):
                local_tracks.append(trackdata.tracks[0])
        return local_tracks

    async def _local_play_all(
        self, ctx: commands.Context, query: Query, from_search=False
    ) -> None:
        if not await self.has_localtracks_check(ctx):
            return None
        if from_search:
            query = Query.process_input(
                query.local_track_path.to_string(),
                self.local_folder_current_path,
                invoked_from="local folder",
            )
        await ctx.invoke(self._search, query=query)

    async def get_all_localtrack_folder_tracks(
        self, ctx: commands.Context, query: Query
    ) -> List[Query]:
        if not await self.has_localtracks_check(ctx):
            return []

        return (
            await query.local_track_path.tracks_in_tree()
            if query.search_subfolders
            else await query.local_track_path.tracks_in_folder()
        )

    async def has_localtracks_check(self, ctx: commands.Context) -> bool:
        folder = LocalPath(None, self.local_folder_current_path)
        if folder.localtrack_folder.exists():
            return True
        if ctx.invoked_with != "start":
            await self._embed_msg(
                ctx, title=_("Invalid Environment"), description=_("No localtracks folder.")
            )
        return False

    async def _build_local_search_list(self, to_search, search_words) -> List[str]:
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
