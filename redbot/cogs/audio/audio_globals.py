from pathlib import Path
from typing import TYPE_CHECKING

from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.dbtools import APSWConnectionWrapper

if TYPE_CHECKING:
    _database_connection: APSWConnectionWrapper
    _bot: Red
    _config: Config
    _localtracks_folder: Path
else:
    _database_connection = None
    _bot = None
    _config = None
    _localtracks_folder = None


def update_audio_globals(config: Config, bot: Red, localtracks_folder: Path):
    global _database_connection, _config, _bot, _localtracks_folder

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


def get_bot() -> Red:
    return _bot


def get_config() -> Config:
    return _config


def get_local_cache_connection() -> APSWConnectionWrapper:
    return _database_connection


def get_localtrack_path() -> Path:
    return _localtracks_folder
