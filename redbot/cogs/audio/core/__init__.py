import asyncio
import datetime
import json

from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping

import aiohttp
import discord

from redbot.core.bot import Red
from redbot.core.commands import Cog
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import Translator, cog_i18n

from ..utils import CacheLevel, PlaylistScope
from . import abc, cog_utils, commands, events, tasks, utilities
from .cog_utils import CompositeMetaClass

_ = Translator("Audio", Path(__file__))


@cog_i18n(_)
class Audio(
    commands.Commands,
    events.Events,
    tasks.Tasks,
    utilities.Utilities,
    Cog,
    metaclass=CompositeMetaClass,
):
    """Play audio through voice channels."""

    def __init__(self, bot: Red):
        super().__init__()
        self.bot = bot
        self.config = None

        self.api_interface = None
        self.player_manager = None
        self.playlist_api = None
        self.local_folder_current_path = None
        self.db_conn = None

        self._error_counter = Counter()
        self._error_timer = {}
        self._disconnected_players = {}
        self._daily_playlist_cache = {}
        self._daily_global_playlist_cache = {}
        self._persist_queue_cache = {}
        self._dj_status_cache = {}
        self._dj_role_cache = {}
        self.skip_votes = {}
        self.play_lock = {}

        self.lavalink_connect_task = None
        self._restore_task = None
        self.player_automated_timer_task = None
        self.cog_cleaned_up = False
        self.lavalink_connection_aborted = False
        self.permission_cache = discord.Permissions(
            embed_links=True,
            read_messages=True,
            send_messages=True,
            read_message_history=True,
            add_reactions=True,
        )

        self.session = aiohttp.ClientSession(json_serialize=json.dumps)
        self.cog_ready_event = asyncio.Event()
        self._ws_resume = defaultdict(asyncio.Event)
        self._ws_op_codes = defaultdict(asyncio.LifoQueue)

        self.cog_init_task = None
        self.global_api_user = {
            "fetched": False,
            "can_read": False,
            "can_post": False,
            "can_delete": False,
        }
        self._ll_guild_updates = set()
        self._diconnected_shard = set()
        self._last_ll_update = datetime.datetime.now(datetime.timezone.utc)
