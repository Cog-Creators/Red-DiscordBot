from abc import ABC
from pathlib import Path
from typing import Final

from redbot import VersionInfo, version_info
from redbot.core import commands
from redbot.core.i18n import Translator

from ..converters import get_lazy_converter, get_playlist_converter

_red_extras = version_info.to_json()
_red_extras.update({"major": 2, "minor": 0, "micro": 0})
__version__ = VersionInfo.from_json(_red_extras)

__author__ = ["aikaterna", "Draper"]

_ = Translator("Audio", Path(__file__).parent)
_SCHEMA_VERSION: Final[int] = 3

LazyGreedyConverter = get_lazy_converter("--")
PlaylistConverter = get_playlist_converter()


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass
