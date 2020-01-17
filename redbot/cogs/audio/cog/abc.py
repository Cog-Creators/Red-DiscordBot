import asyncio
from abc import ABC, abstractmethod
from collections import Counter
from typing import List, Mapping, MutableMapping, Optional

import aiohttp
import discord
import lavalink

from redbot.cogs.audio.apis.interface import AudioAPIInterface
from redbot.cogs.audio.manager import ServerManager
from redbot.core import Config, commands
from redbot.core.bot import Red


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    bot: Red
    config: Config
    skip_votes: MutableMapping[discord.Guild, List[discord.Member]]
    play_lock: MutableMapping[int, bool]
    _daily_playlist_cache: MutableMapping[int, bool]
    _dj_status_cache: MutableMapping[int, Optional[bool]]
    _dj_role_cache: MutableMapping[int, Optional[int]]
    _session: aiohttp.ClientSession
    _connect_task: Optional[asyncio.Task]
    _disconnect_task: Optional[asyncio.Task]
    _cleaned_up: bool
    _connection_aborted: bool
    _manager: Optional[ServerManager]
    api_interface: Optional[AudioAPIInterface]
    _error_counter: Counter
    _error_timer: MutableMapping[int, float]
    _disconnected_players: MutableMapping[int, bool]
    _init_task: asyncio.Task
    _ready_event: asyncio.Event
    _default_lavalink_settings: Mapping

    @abstractmethod
    async def llsetup(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    async def _embed_msg(self, ctx: commands.Context, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    async def error_reset(self, player: lavalink.Player):
        raise NotImplementedError()

    @abstractmethod
    async def _status_check(self, track, playing_servers):
        raise NotImplementedError()

    @abstractmethod
    async def _players_check(self):
        raise NotImplementedError()

    @abstractmethod
    async def increase_error_counter(self, player: lavalink.Player) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def _close_database(self):
        raise NotImplementedError()

    @abstractmethod
    async def _process_db(self, ctx: commands.Context):
        raise NotImplementedError()

    @abstractmethod
    def _play_lock(self, ctx: commands.Context, true_or_false: bool):
        raise NotImplementedError()

    @abstractmethod
    async def initialize(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def _migrate_config(self, from_version: int, to_version: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    def _restart_connect(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def attempt_connect(self, timeout: int = 50) -> None:
        raise NotImplementedError()
