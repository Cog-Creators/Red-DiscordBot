from pathlib import Path
from typing import TYPE_CHECKING, Tuple

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.dbtools import APSWConnectionWrapper

if TYPE_CHECKING:
    from .apis.playlist_wrapper import PlaylistWrapper

    _database_connection: APSWConnectionWrapper
    _bot: Red
    _config: Config
    _localtracks_folder: Path
    _playlist_api: PlaylistWrapper
else:
    _database_connection = None
    _bot = None
    _config = None
    _localtracks_folder = None
    _playlist_api = None


async def update_audio_globals(
    config: Config, bot: Red, localtracks_folder: Path
) -> Tuple[APSWConnectionWrapper, Config, Red, Path, "PlaylistWrapper"]:
    global _database_connection, _config, _bot, _localtracks_folder, _playlist_api

    if _config is None:
        _config = config
    if _bot is None:
        _bot = bot

    if _localtracks_folder is None:
        _localtracks_folder = localtracks_folder

    if _database_connection is None:
        _database_connection = APSWConnectionWrapper(
            str(cog_data_path(_bot.get_cog("Audio")) / "Audio.db")
        )
    if _playlist_api is None:
        from .apis.playlist_wrapper import PlaylistWrapper

        _playlist_api = PlaylistWrapper(_config, _database_connection)
        await _playlist_api.init()
    return _database_connection, _config, _bot, _localtracks_folder, _playlist_api


def get_bot() -> Red:
    return _bot


def get_config() -> Config:
    return _config


def get_database_connection() -> APSWConnectionWrapper:
    return _database_connection


def get_localtrack_path() -> Path:
    return _localtracks_folder


def get_playlist_api_wrapper() -> "PlaylistWrapper":
    return _playlist_api
