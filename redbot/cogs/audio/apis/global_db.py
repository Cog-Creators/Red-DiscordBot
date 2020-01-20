import logging

import aiohttp

from redbot.core import Config
from redbot.core.bot import Red

_API_URL = "https://redbot.app/"

log = logging.getLogger("red.cogs.Audio.api.GlobalDB")


class GlobalCacheWrapper:
    def __init__(self, bot: Red, config: Config, session: aiohttp.ClientSession):
        # Place Holder for the Global Cache PR
        self.bot = bot
        self.config = config
        self.session = session
        self.api_key = None
        self._handshake_token = ""
        self.can_write = False
        self._handshake_token = ""
