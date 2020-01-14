import logging
from typing import Optional

import aiohttp

from ..audio_globals import get_bot
from ..errors import YouTubeApiError

log = logging.getLogger("red.cogs.Audio.api.YouTube")

SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"


class YouTubeWrapper:
    """Wrapper for the YouTube Data API."""

    def __init__(self, session: aiohttp.ClientSession):
        self.bot = get_bot()
        self.session = session
        self.api_key = None

    async def _get_api_key(self,) -> str:
        tokens = await self.bot.get_shared_api_tokens("youtube")
        self.api_key = tokens.get("api_key", "")
        return self.api_key

    async def get_call(self, query: str) -> Optional[str]:
        params = {
            "q": query,
            "part": "id",
            "key": await self._get_api_key(),
            "maxResults": 1,
            "type": "video",
        }
        async with self.session.request("GET", SEARCH_ENDPOINT, params=params) as r:
            if r.status in [400, 404]:
                return None
            elif r.status in [403, 429]:
                if r.reason == "quotaExceeded":
                    raise YouTubeApiError("Your YouTube Data API quota has been reached.")
                return None
            else:
                search_response = await r.json()
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                return f"https://www.youtube.com/watch?v={search_result['id']['videoId']}"
