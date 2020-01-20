import logging

from .lavalink import LavalinkTasks
from .player import PlayerTasks
from .startup import StartUpTasks
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Tasks")


class Tasks(LavalinkTasks, PlayerTasks, StartUpTasks, metaclass=CompositeMetaClass):
    """Class joining all task subclasses"""
