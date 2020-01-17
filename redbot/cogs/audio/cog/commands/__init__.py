from .audioset import AudioSetCommands
from .equalizer import EqualizerCommands
from .llset import LavalinkSetCommands
from .localtracks import LocalTracksCommands
from .playlists import PlayListCommands
from .queue import QueueCommands
from ..utils import CompositeMetaClass


class Commands(
    AudioSetCommands,
    EqualizerCommands,
    LavalinkSetCommands,
    LocalTracksCommands,
    PlayListCommands,
    QueueCommands,
    metaclass=CompositeMetaClass,
):
    pass
