from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from redbot.core import Config

from . import constants
from ._internal.playlists.enums import PlaylistScope
from ._internal.setting_cache import SettingCacheManager

if TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["config_cache", "_init", "_bot_ref"]

_config: Optional[Config] = None
_bot_ref: Optional[Red] = None
config_cache: Optional[SettingCacheManager] = None


async def _init(bot: Red):
    global _config
    global _bot_ref
    global config_cache
    _bot_ref = bot
    _config = Config.get_conf(None, 2711759130, force_registration=True, cog_name="Audio")
    config_cache = SettingCacheManager(bot, _config, enable_cache=True)
    _config.init_custom("EQUALIZER", 1)
    _config.init_custom(PlaylistScope.GLOBAL.value, 1)
    _config.init_custom(PlaylistScope.GUILD.value, 2)
    _config.init_custom(PlaylistScope.USER.value, 2)
    _config.register_custom("EQUALIZER", **constants.DEFAULT_COG_EQUALIZER_SETTINGS)
    _config.register_custom(PlaylistScope.GLOBAL.value, **constants.DEFAULT_COG_PLAYLISTS_SETTINGS)
    _config.register_custom(PlaylistScope.GUILD.value, **constants.DEFAULT_COG_PLAYLISTS_SETTINGS)
    _config.register_custom(PlaylistScope.USER.value, **constants.DEFAULT_COG_PLAYLISTS_SETTINGS)
    _config.register_guild(**constants.DEFAULT_COG_GUILD_SETTINGS)
    _config.register_global(**constants.DEFAULT_COG_GLOBAL_SETTINGS)
    _config.register_user(**constants.DEFAULT_COG_USER_SETTINGS)
    _config.register_channel(**constants.DEFAULT_COG_CHANNEL_SETTINGS)
