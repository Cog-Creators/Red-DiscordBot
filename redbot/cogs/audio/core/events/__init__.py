import logging

from .cog import AudioEvents
from .dpy import DpyEvents
from .lavalink import LavalinkEvents
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Events")


class Events(AudioEvents, DpyEvents, LavalinkEvents, metaclass=CompositeMetaClass):
    """Class joining all event subclasses"""
