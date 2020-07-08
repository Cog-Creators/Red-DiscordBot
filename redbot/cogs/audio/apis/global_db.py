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

_API_URL = "https://redbot.app/"

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
