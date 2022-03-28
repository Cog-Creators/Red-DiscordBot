from red_commons.logging import getLogger

from ..cog_utils import CompositeMetaClass
from .cog import AudioEvents
from .dpy import DpyEvents
from .lavalink import LavalinkEvents
from .red import BlueEvents

log = getLogger("red.cogs.Audio.cog.Events")


class Events(AudioEvents, DpyEvents, LavalinkEvents, BlueEvents, metaclass=CompositeMetaClass):
    """Class joining all event subclasses"""
