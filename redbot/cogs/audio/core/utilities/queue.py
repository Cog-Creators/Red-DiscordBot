import logging
import math
from pathlib import Path

from typing import List, Tuple

import lavalink

from fuzzywuzzy import process
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter

from ...audio_dataclasses import Query
from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Utilities.queue")
_ = Translator("Audio", Path(__file__))


class QueueUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def _build_queue_search_list(
        self, queue_list: List[lavalink.Track], search_words: str
    ) -> List[Tuple[int, str]]:
        track_list = []
        async for queue_idx, track in AsyncIter(queue_list).enumerate(start=1):
            if not self.match_url(track.uri):
                query = Query.process_input(track, self.local_folder_current_path)
                if (
                    query.is_local
                    and query.local_track_path is not None
                    and track.title == "Unknown title"
                ):
                    track_title = query.local_track_path.to_string_user()
                else:
                    track_title = "{} - {}".format(track.author, track.title)
            else:
                track_title = track.title

            song_info = {str(queue_idx): track_title}
            track_list.append(song_info)
        search_results = process.extract(search_words, track_list, limit=50)
        search_list = []
        async for search, percent_match in AsyncIter(search_results):
            async for queue_position, title in AsyncIter(search.items()):
                if percent_match > 89:
                    search_list.append((queue_position, title))
        return search_list
