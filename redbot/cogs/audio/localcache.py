# -*- coding: utf-8 -*-
import asyncio
import atexit
import json
import os.path
from typing import Dict, Tuple, Union

import aiofiles

from appdirs import AppDirs

__all__ = ["music_cache"]
PRETTY: Dict[str, Union[int, bool, Tuple[str, str]]] = {
    "indent": 4,
    "sort_keys": False,
    "separators": (",", " : "),
}
dirs = AppDirs("Red-DiscordBot", "Audio")
CACHE_FILE = str(os.path.join(dirs.user_data_dir, "audio.cache"))


class YouTubeCacheConfigClass(object):
    def __init__(self):
        self.cache = None
        self._file_name = CACHE_FILE

    async def get_file_cache(self):
        async with aiofiles.open(self._file_name, mode="r") as stream:
            return json.loads(await stream.read())

    def save_to_file(self, settings=None, unload=False):
        if settings is None:
            settings = PRETTY

        async def save_file_cache():
            async with aiofiles.open(YouTubeCacheConfig._file_name, mode="w") as stream:
                if self.cache is not None:
                    await stream.write(json.dumps(self.cache, **settings))

        if not unload:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(save_file_cache())
        else:
            return save_file_cache

    async def get_cache(self):
        if self.cache is None:
            try:
                self.cache = await self.get_file_cache()
            except (IOError, ValueError):
                self.cache = {}

            atexit.register(lambda: self.save_to_file())
        return self.cache

    async def get_song(self, song_info):
        if self.cache is None:
            self.cache = await self.get_cache()
        if song_info in self.cache:
            return self.cache[song_info]
        else:
            return False

    async def update_cache(self, song_info, url):
        if self.cache is None:
            self.cache = await self.get_cache()
        self.cache[song_info] = url

    @staticmethod
    async def youtube_api_search(yt_key, query, session):
        params = {"q": query, "part": "id", "key": yt_key, "maxResults": 1, "type": "video"}
        yt_url = "https://www.googleapis.com/youtube/v3/search"
        async with session.request("GET", yt_url, params=params) as r:
            if r.status == 400:
                return None
            else:
                search_response = await r.json()
        for search_result in search_response.get("items", []):
            if search_result["id"]["kind"] == "youtube#video":
                return f"https://www.youtube.com/watch?v={search_result['id']['videoId']}"


YouTubeCacheConfig = YouTubeCacheConfigClass()


class music_cache(object):
    @classmethod
    async def get_url(cls, yt_key, song_info, session):
        song_data = await YouTubeCacheConfig.get_song(song_info)
        if song_data is False:
            url = await YouTubeCacheConfig.youtube_api_search(yt_key, song_info, session)
            if url:
                await YouTubeCacheConfig.update_cache(song_info, url)
            return url
        else:
            return song_data

    @staticmethod
    def _save_cache():
        return YouTubeCacheConfig.save_to_file(unload=True)
