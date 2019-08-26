from redbot.core import Config
from redbot.core.bot import Red

# noinspection PyProtectedMember
from .converters import _pass_config_to_converters
from .dataclasses import _pass_config_to_dataclasses
from .menus import _pass_config_to_menus

# noinspection PyProtectedMember
from .playlists import _pass_config_to_playlist

# noinspection PyProtectedMember
from .utils import _pass_config_to_utils


def pass_config_to_dependencies(config: Config, bot: Red, localtracks_folder: str):
    _pass_config_to_utils(config, bot)
    _pass_config_to_playlist(config, bot)
    _pass_config_to_converters(config, bot)
    _pass_config_to_menus(config, bot)
    _pass_config_to_dataclasses(config, bot, localtracks_folder)
