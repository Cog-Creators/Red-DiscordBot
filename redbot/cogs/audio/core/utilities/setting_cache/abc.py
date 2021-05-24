from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from redbot.core import Config
from redbot.core.bot import Red

if TYPE_CHECKING:
    from . import SettingCacheManager


class CachingABC(ABC):
    _config: Config
    bot: Red
    enable_cache: bool
    config_cache: SettingCacheManager

    @abstractmethod
    async def get_context_value(self, *args, **kwargs):
        raise NotImplementedError()

    def reset_globals(self) -> None:
        pass


class CacheBase(CachingABC, ABC):
    def __init__(self, bot: Red, config: Config, enable_cache: bool, cache: SettingCacheManager):
        self._config = config
        self.bot = bot
        self.enable_cache = enable_cache
        self.config_cache = cache
