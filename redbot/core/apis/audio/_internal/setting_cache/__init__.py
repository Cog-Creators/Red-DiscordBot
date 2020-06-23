from __future__ import annotations

from redbot.core import Config
from redbot.core.bot import Red

from .autodc import AutoDCManager
from .autoplay import AutoPlayManager
from .blacklist_whitelist import WhitelistBlacklistManager
from .channel_restrict import ChannelRestrictManager
from .country_code import CountryCodeManager
from .daily_global_playlist import DailyGlobalPlaylistManager
from .daily_playlist import DailyPlaylistManager
from .dj_roles import DJRoleManager
from .dj_status import DJStatusManager
from .emptydc import EmptyDCManager
from .emptydc_timer import EmptyDCTimerManager
from .emptypause import EmptyPauseManager
from .emptypause_timer import EmptyPauseTimerManager
from .globaldb import GlobalDBManager
from .globaldb_timeout import GlobalDBTimeoutManager
from .jukebox import JukeboxManager
from .jukebox_price import JukeboxPriceManager
from .local_cache_age import LocalCacheAgeManager
from .local_cache_level import LocalCacheLevelManager
from .localpath import LocalPathManager
from .lyrics import PreferLyricsManager
from .managed_lavalink_auto_update import LavalinkAutoUpdateManager
from .managed_lavalink_server import ManagedLavalinkManager
from .max_track_length import MaxTrackLengthManager
from .notify import NotifyManager
from .persist_queue import PersistentQueueManager
from .repeat import RepeatManager
from .restrict import URLRestrictManager
from .shuffle import ShuffleManager
from .shuffle_bumped import ShuffleBumpedManager
from .status import StatusManager
from .thumbnail import ThumbnailManager
from .vc_restricted import VCRestrictedManager
from .volume import VolumeManager
from .votes_percentage import VotesPercentageManager
from .voting import VotingManager

__all__ = ["SettingCacheManager"]


class SettingCacheManager:
    def __init__(self, bot: Red, config: Config, enable_cache: bool = True) -> None:
        self._config: Config = config
        self.bot: Red = bot
        self.enabled = enable_cache

        self.blacklist_whitelist = WhitelistBlacklistManager(bot, config, self.enabled)
        self.dj_roles = DJRoleManager(bot, config, self.enabled)
        self.dj_status = DJStatusManager(bot, config, self.enabled)
        self.daily_playlist = DailyPlaylistManager(bot, config, self.enabled)
        self.daily_global_playlist = DailyGlobalPlaylistManager(bot, config, self.enabled)
        self.persistent_queue = PersistentQueueManager(bot, config, self.enabled)
        self.votes = VotingManager(bot, config, self.enabled)
        self.votes_percentage = VotesPercentageManager(bot, config, self.enabled)
        self.shuffle = ShuffleManager(bot, config, self.enabled)
        self.shuffle_bumped = ShuffleBumpedManager(bot, config, self.enabled)
        self.autoplay = AutoPlayManager(bot, config, self.enabled)
        self.thumbnail = ThumbnailManager(bot, config, self.enabled)
        self.localpath = LocalPathManager(bot, config, self.enabled)
        self.disconnect = AutoDCManager(bot, config, self.enabled)
        self.empty_dc = EmptyDCManager(bot, config, self.enabled)
        self.empty_dc_timer = EmptyDCTimerManager(bot, config, self.enabled)
        self.empty_pause = EmptyPauseManager(bot, config, self.enabled)
        self.empty_pause_timer = EmptyPauseTimerManager(bot, config, self.enabled)
        self.global_api = GlobalDBManager(bot, config, self.enabled)
        self.global_api_timeout = GlobalDBTimeoutManager(bot, config, self.enabled)
        self.local_cache_level = LocalCacheLevelManager(bot, config, self.enabled)
        self.country_code = CountryCodeManager(bot, config, self.enabled)
        self.repeat = RepeatManager(bot, config, self.enabled)
        self.channel_restrict = ChannelRestrictManager(bot, config, self.enabled)
        self.volume = VolumeManager(bot, config, self.enabled)
        self.local_cache_age = LocalCacheAgeManager(bot, config, self.enabled)
        self.jukebox = JukeboxManager(bot, config, self.enabled)
        self.jukebox_price = JukeboxPriceManager(bot, config, self.enabled)
        self.max_track_length = MaxTrackLengthManager(bot, config, self.enabled)
        self.prefer_lyrics = PreferLyricsManager(bot, config, self.enabled)
        self.notify = NotifyManager(bot, config, self.enabled)
        self.status = StatusManager(bot, config, self.enabled)
        self.url_restrict = URLRestrictManager(bot, config, self.enabled)
        self.managed_lavalink_server = ManagedLavalinkManager(bot, config, self.enabled)
        self.managed_lavalink_server_auto_update = LavalinkAutoUpdateManager(
            bot, config, self.enabled
        )
        self.vc_restricted = VCRestrictedManager(bot, config, self.enabled)
