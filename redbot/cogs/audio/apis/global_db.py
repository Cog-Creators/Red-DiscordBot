import hashlib
import logging
import urllib.parse
import uuid
from typing import Optional

import aiohttp
from lavalink.rest_api import LoadResult

from ..audio_dataclasses import Query
from ..audio_globals import get_bot, get_config
from ..audio_logging import debug_exc_log, IS_DEBUG

_API_URL = "https://redbot.app/"
_WRITE_GLOBAL_API_ACCESS = None

log = logging.getLogger("red.cogs.Audio.api.GlobalDB")


class GlobalCacheWrapper:
    def __init__(self, session: aiohttp.ClientSession):
        self.bot = get_bot()
        self.config = get_config()
        self.session = session
        self.api_key = None
        self._handshake_token = ""
        self.can_write = _WRITE_GLOBAL_API_ACCESS

    async def get_api_key(self,) -> Optional[str]:
        global _WRITE_GLOBAL_API_ACCESS
        tokens = await self.bot.get_shared_api_tokens("audiodb")
        self.api_key = tokens.get("api_key", None)
        self.can_write = _WRITE_GLOBAL_API_ACCESS = self.api_key is not None
        id_list = list(self.bot._co_owners)
        id_list.append(self.bot.owner_id)
        self._handshake_token = "||".join(list(map(self.uuid_from_id, id_list)))
        return self.api_key

    @staticmethod
    def uuid_from_id(seed: str) -> str:
        m = hashlib.md5()
        m.update(f"{seed}".encode("utf-8"))
        return f"{uuid.UUID(m.hexdigest())}"

    async def get_call(self, query: Optional[Query] = None) -> Optional[dict]:
        api_url = f"{_API_URL}api/v1/queries"
        search_response = "error"
        try:
            query = Query.process_input(query)
            if any([not query or not query.valid or query.is_spotify or query.is_local]):
                return {}
            await self.get_api_key()
            query = query.lavalink_query
            async with self.session.get(
                api_url,
                timeout=aiohttp.ClientTimeout(total=await self.config.global_db_get_timeout()),
                headers={"X-Token": self._handshake_token},
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

    async def get_spotify(self, title: str, author: Optional[str]) -> Optional[dict]:
        api_url = f"{_API_URL}api/v1/queries/spotify"
        search_response = "error"
        try:
            params = {"title": urllib.parse.quote(title), "author": urllib.parse.quote(author)}
            await self.get_api_key()
            async with self.session.get(
                api_url,
                timeout=aiohttp.ClientTimeout(total=await self.config.global_db_get_timeout()),
                headers={"X-Token": self._handshake_token},
                params=params,
            ) as r:
                search_response = await r.json()
                if IS_DEBUG and "x-process-time" in r.headers:
                    log.debug(
                        f"GET/spotify || Ping {r.headers.get('x-process-time')} || "
                        f"Status code {r.status} || {title} - {author}"
                    )
            if "tracks" not in search_response:
                return None
            return search_response
        except Exception as err:
            debug_exc_log(log, err, f"Failed to Get query: {api_url}")
        return {}

    async def post_call(self, llresponse: LoadResult, query: Optional[Query]) -> None:
        api_url = f"{_API_URL}api/v1/queries"
        try:
            query = Query.process_input(query)
            if llresponse.has_error or llresponse.load_type.value in ["NO_MATCHES", "LOAD_FAILED"]:
                return
            if query and query.valid and not query.is_local and not query.is_spotify:
                query = query.lavalink_query
            else:
                return None
            await self.get_api_key()
            if self.api_key is None:
                return None
            async with self.session.post(
                api_url,
                json=llresponse._raw,
                headers={"Authorization": self.api_key, "X-Token": self._handshake_token},
                params={"query": urllib.parse.quote(query)},
            ) as r:
                await r.read()
                if IS_DEBUG and "x-process-time" in r.headers:
                    log.debug(
                        f"POST || Ping {r.headers.get('x-process-time')} ||"
                        f" Status code {r.status} || {query}"
                    )
        except Exception as err:
            debug_exc_log(log, err, f"Failed to post query: {query}")
