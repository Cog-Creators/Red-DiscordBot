from abc import ABC, abstractmethod

import discord

from redbot.core import Config
from redbot.core.bot import Red


class CachingABC(ABC):
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.bot = bot
        self.enable_cache = enable_cache

    @abstractmethod
    async def get_context_value(self, *args, **kwargs):
        raise NotImplementedError()

    def reset_globals(self) -> None:
        pass
