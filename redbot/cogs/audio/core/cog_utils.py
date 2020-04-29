from abc import ABC
from pathlib import Path
from typing import Final

from redbot import VersionInfo
from redbot.core import commands
from redbot.core.i18n import Translator

from ..converters import get_lazy_converter, get_playlist_converter

__version__ = VersionInfo.from_json({"major": 2, "minor": 0, "micro": 0, "releaselevel": "final"})

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
