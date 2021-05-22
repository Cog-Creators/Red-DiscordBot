from __future__ import annotations

import attr

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
from .max_queue_size import MaxQueueSizerManager
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
from .auto_deafen import AutoDeafenManager

__all__ = ["SettingCacheManager"]


def cache_factory(cls):
    def factory(self: SettingCacheManager):
        return cls(self.bot, self.config, self.enabled)

    return attr.Factory(factory, takes_self=True)


@attr.s(auto_attribs=True)
class SettingCacheManager:
    bot: Red
    config: Config
    enabled: bool

    blacklist_whitelist: WhitelistBlacklistManager = cache_factory(WhitelistBlacklistManager)
    dj_roles: DJRoleManager = cache_factory(DJRoleManager)
    dj_status: DJStatusManager = cache_factory(DJStatusManager)
    daily_playlist: DailyPlaylistManager = cache_factory(DailyPlaylistManager)
    daily_global_playlist: DailyGlobalPlaylistManager = cache_factory(DailyGlobalPlaylistManager)
    persistent_queue: PersistentQueueManager = cache_factory(PersistentQueueManager)
    votes: VotingManager = cache_factory(VotingManager)
    votes_percentage: VotesPercentageManager = cache_factory(VotesPercentageManager)
    shuffle: ShuffleManager = cache_factory(ShuffleManager)
    shuffle_bumped: ShuffleBumpedManager = cache_factory(ShuffleBumpedManager)
    autoplay: AutoPlayManager = cache_factory(AutoPlayManager)
    thumbnail: ThumbnailManager = cache_factory(ThumbnailManager)
    localpath: LocalPathManager = cache_factory(LocalPathManager)
    disconnect: AutoDCManager = cache_factory(AutoDCManager)
    empty_dc: EmptyDCManager = cache_factory(EmptyDCManager)
    empty_dc_timer: EmptyDCTimerManager = cache_factory(EmptyDCTimerManager)
    empty_pause: EmptyPauseManager = cache_factory(EmptyPauseManager)
    empty_pause_timer: EmptyPauseTimerManager = cache_factory(EmptyPauseTimerManager)
    global_api: GlobalDBManager = cache_factory(GlobalDBManager)
    global_api_timeout: GlobalDBTimeoutManager = cache_factory(GlobalDBTimeoutManager)
    local_cache_level: LocalCacheLevelManager = cache_factory(LocalCacheLevelManager)
    country_code: CountryCodeManager = cache_factory(CountryCodeManager)
    repeat: RepeatManager = cache_factory(RepeatManager)
    channel_restrict: ChannelRestrictManager = cache_factory(ChannelRestrictManager)
    volume: VolumeManager = cache_factory(VolumeManager)
    local_cache_age: LocalCacheAgeManager = cache_factory(LocalCacheAgeManager)
    jukebox: JukeboxManager = cache_factory(JukeboxManager)
    jukebox_price: JukeboxPriceManager = cache_factory(JukeboxPriceManager)
    max_track_length: MaxTrackLengthManager = cache_factory(MaxTrackLengthManager)
    prefer_lyrics: PreferLyricsManager = cache_factory(PreferLyricsManager)
    notify: NotifyManager = cache_factory(NotifyManager)
    status: StatusManager = cache_factory(StatusManager)
    url_restrict: URLRestrictManager = cache_factory(URLRestrictManager)
    managed_lavalink_server: ManagedLavalinkManager = cache_factory(ManagedLavalinkManager)
    managed_lavalink_server_auto_update: LavalinkAutoUpdateManager = cache_factory(
        LavalinkAutoUpdateManager
    )
    vc_restricted: VCRestrictedManager = cache_factory(VCRestrictedManager)
    auto_deafen: AutoDeafenManager = cache_factory(AutoDeafenManager)
    max_queue_size: MaxQueueSizerManager = cache_factory(MaxQueueSizerManager)

    def reset_globals(self):
        for name, value in attr.asdict(self, recurse=False).items():
            if name not in ("bot", "config", "enabled"):
                value.reset_globals()
