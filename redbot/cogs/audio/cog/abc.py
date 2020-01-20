import asyncio
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
from typing import List, Mapping, MutableMapping, Optional

import aiohttp
import discord
import lavalink

from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.dbtools import APSWConnectionWrapper
from ..apis.interface import AudioAPIInterface
from ..apis.playlist_wrapper import PlaylistWrapper
from ..manager import ServerManager


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    bot: Red
    config: Config
    api_interface: Optional[AudioAPIInterface]
    player_manager: Optional[ServerManager]
    playlist_api: Optional[PlaylistWrapper]
    local_folder_current_path: Optional[Path]
    db_conn: Optional[APSWConnectionWrapper]
    session: aiohttp.ClientSession

    skip_votes: MutableMapping[discord.Guild, List[discord.Member]]
    play_lock: MutableMapping[int, bool]
    _daily_playlist_cache: MutableMapping[int, bool]
    _dj_status_cache: MutableMapping[int, Optional[bool]]
    _dj_role_cache: MutableMapping[int, Optional[int]]
    _error_timer: MutableMapping[int, float]
    _disconnected_players: MutableMapping[int, bool]

    cog_cleaned_up: bool
    lavalink_connection_aborted: bool

    _error_counter: Counter

    lavalink_connect_task: Optional[asyncio.Task]
    player_automated_timer_task: Optional[asyncio.Task]
    cog_init_task: asyncio.Task
    cog_ready_event: asyncio.Event

    _default_lavalink_settings: Mapping

    @abstractmethod
    async def _llsetup(self, ctx: commands.Context):
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
    async def data_schema_migration(self, from_version: int, to_version: int) -> None:
        raise NotImplementedError()

    @abstractmethod
    def lavalink_restart_connect(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def lavalink_attempt_connect_task(self, timeout: int = 50) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def player_automated_timer(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def lavalink_event_handler(
        self, player: lavalink.Player, event_type: lavalink.LavalinkEvents, extra
    ) -> None:
        raise NotImplementedError()
