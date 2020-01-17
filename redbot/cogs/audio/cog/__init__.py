import asyncio
from collections import Counter

import aiohttp

from redbot.core import Config
from redbot.core.data_manager import cog_data_path
from redbot.core.i18n import cog_i18n
from .abc import MixinMeta
from .commands import Commands
from .events import Events
from .listeners import Listeners
from .tasks import Tasks
from .utilities import Utilities
from .utils import _
from ..utils import PlaylistScope


@cog_i18n(_)
class Audio(MixinMeta, Commands, Events, Listeners, Tasks, Utilities, commands.Cog):
    """Play audio through voice channels."""

    _default_lavalink_settings = {
        "host": "localhost",
        "rest_port": 2333,
        "ws_port": 2333,
        "password": "youshallnotpass",
    }

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 2711759130, force_registration=True)
        self.skip_votes = {}
        self.play_lock = {}
        self._daily_playlist_cache = {}
        self._dj_status_cache = {}
        self._dj_role_cache = {}
        self.session = aiohttp.ClientSession()
        self._connect_task = None
        self._disconnect_task = None
        self._cleaned_up: bool = False
        self._connection_aborted: bool = False
        self._manager = None
        default_global = dict(
            schema_version=1,
            cache_level=0,
            cache_age=365,
            global_db_enabled=False,
            global_db_get_timeout=5,  # Here as a placeholder in case we want to enable the command
            status=False,
            use_external_lavalink=False,
            restrict=True,
            localpath=str(cog_data_path(raw_name="Audio")),
            url_keyword_blacklist=[],
            url_keyword_whitelist=[],
            **self._default_lavalink_settings,
        )

        default_guild = dict(
            auto_play=False,
            autoplaylist=dict(enabled=False, id=None, name=None, scope=None),
            disconnect=False,
            dj_enabled=False,
            dj_role=None,
            daily_playlists=False,
            emptydc_enabled=False,
            emptydc_timer=0,
            emptypause_enabled=False,
            emptypause_timer=0,
            jukebox=False,
            jukebox_price=0,
            maxlength=0,
            notify=False,
            repeat=False,
            shuffle=False,
            shuffle_bumped=True,
            thumbnail=False,
            volume=100,
            vote_enabled=False,
            vote_percent=0,
            room_lock=None,
            url_keyword_blacklist=[],
            url_keyword_whitelist=[],
        )
        _playlist = dict(id=None, author=None, name=None, playlist_url=None, tracks=[])
        self.config.init_custom("EQUALIZER", 1)
        self.config.register_custom("EQUALIZER", eq_bands=[], eq_presets={})
        self.config.init_custom(PlaylistScope.GLOBAL.value, 1)
        self.config.register_custom(PlaylistScope.GLOBAL.value, **_playlist)
        self.config.init_custom(PlaylistScope.GUILD.value, 2)
        self.config.register_custom(PlaylistScope.GUILD.value, **_playlist)
        self.config.init_custom(PlaylistScope.USER.value, 2)
        self.config.register_custom(PlaylistScope.USER.value, **_playlist)
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.api_interface = None
        self._error_counter = Counter()
        self._error_timer = {}
        self._disconnected_players = {}

        # These has to be a task since this requires the bot to be ready
        # If it waits for ready in startup, we cause a deadlock during initial load
        # as initial load happens before the bot can ever be ready.
        self._init_task = self.bot.loop.create_task(self.initialize())
        self._ready_event = asyncio.Event()
