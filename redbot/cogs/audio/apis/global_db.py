import asyncio
import contextlib
import logging
import urllib.parse
from typing import Mapping, Optional, TYPE_CHECKING, Union

import aiohttp
from lavalink.rest_api import LoadResult

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog

from ..audio_dataclasses import Query
from ..audio_logging import IS_DEBUG, debug_exc_log

if TYPE_CHECKING:
    from .. import Audio

_API_URL = "https://api.redbot.app"

log = logging.getLogger("red.cogs.Audio.api.GlobalDB")


class GlobalCacheWrapper:
    def __init__(
        self, bot: Red, config: Config, session: aiohttp.ClientSession, cog: Union["Audio", Cog]
    ):
        # Place Holder for the Global Cache PR
        self.bot = bot
        self.config = config
        self.session = session
        self.api_key = None
        self._handshake_token = ""
        self.can_write = False
        self._handshake_token = ""
        self.has_api_key = None
        self._token: Mapping[str, str] = {}
        self.cog = cog

    def update_token(self, new_token: Mapping[str, str]):
        self._token = new_token

    async def _get_api_key(self,) -> Optional[str]:
        if not self._token:
            self._token = await self.bot.get_shared_api_tokens("audiodb")
        self.api_key = self._token.get("api_key", None)
        self.has_api_key = self.api_key is not None
        id_list = set(self.bot._co_owners)
        id_list.update(self.bot.owner_id)
        id_list.update(self.bot.owner_ids)
        id_list = list(id_list)
        self._handshake_token = "||".join(map(str, id_list))
        return self.api_key

    async def get_call(self, query: Optional[Query] = None) -> dict:
        api_url = f"{_API_URL}/api/v1/queries"
        try:
            query = Query.process_input(query, self.cog.local_folder_current_path)
            if any([not query or not query.valid or query.is_spotify or query.is_local]):
                return {}
            await self._get_api_key()
            search_response = {}
            query = query.lavalink_query
            with contextlib.suppress(aiohttp.ContentTypeError, asyncio.TimeoutError):
                async with self.session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=await self.config.global_db_get_timeout()),
                    headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                    params={"query": urllib.parse.quote(query)},
                ) as r:
                    search_response = await r.json()
                    if IS_DEBUG and "x-process-time" in r.headers:
                        log.debug(
                            f"GET || Ping {r.headers.get('x-process-time')} || "
                            f"Status code {r.status} || {query}"
                        )
            if "tracks" not in search_response:
                return {}
            return search_response
        except Exception as err:
            debug_exc_log(log, err, f"Failed to Get query: {api_url}/{query}")
        return {}

    async def get_spotify(self, title: str, author: Optional[str]) -> dict:
        api_url = f"{_API_URL}/api/v1/queries/spotify"
        try:
            search_response = "error"
            params = {"title": urllib.parse.quote(title), "author": urllib.parse.quote(author)}
            await self._get_api_key()
            with contextlib.suppress(aiohttp.ContentTypeError, asyncio.TimeoutError):
                async with self.session.get(
                    api_url,
                    timeout=aiohttp.ClientTimeout(total=await self.config.global_db_get_timeout()),
                    headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                    params=params,
                ) as r:
                    search_response = await r.json()
                    if IS_DEBUG and "x-process-time" in r.headers:
                        log.debug(
                            f"GET/spotify || Ping {r.headers.get('x-process-time')} || "
                            f"Status code {r.status} || {title} - {author}"
                        )
            if "tracks" not in search_response:
                return {}
            return search_response
        except Exception as err:
            debug_exc_log(log, err, f"Failed to Get query: {api_url}")
        return {}

    async def post_call(self, llresponse: LoadResult, query: Optional[Query]) -> None:
        try:
            query = Query.process_input(query, self.cog.local_folder_current_path)
            if llresponse.has_error or llresponse.load_type.value in ["NO_MATCHES", "LOAD_FAILED"]:
                await asyncio.sleep(0)
                return
            if query and query.valid and query.is_youtube:
                query = query.lavalink_query
            else:
                await asyncio.sleep(0)
                return None
            await self._get_api_key()
            if self.api_key is None:
                await asyncio.sleep(0)
                return None
            api_url = f"{_API_URL}/api/v1/queries"
            async with self.session.post(
                api_url,
                json=llresponse._raw,
                headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                params={"query": urllib.parse.quote(query)},
            ) as r:
                output = await r.read()
                if IS_DEBUG and "x-process-time" in r.headers:
                    log.debug(
                        f"POST || Ping {r.headers.get('x-process-time')} ||"
                        f" Status code {r.status} || {query}"
                    )
        except Exception as err:
            debug_exc_log(log, err, f"Failed to post query: {query}")
        await asyncio.sleep(0)

    async def update_global(self, llresponse: LoadResult, query: Optional[Query] = None):
        await self.post_call(llresponse=llresponse, query=query)
