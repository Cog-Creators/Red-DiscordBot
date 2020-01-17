from abc import ABC
from pathlib import Path

from redbot.core import commands
from redbot.core.i18n import Translator

from ..converters import get_lazy_converter, get_playlist_converter


__version__ = "1.1.0"
__author__ = ["aikaterna", "Draper"]

_ = Translator("Audio", Path(__file__).parent)
_SCHEMA_VERSION = 3

LazyGreedyConverter = get_lazy_converter("--")
PlaylistConverter = get_playlist_converter()


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass
