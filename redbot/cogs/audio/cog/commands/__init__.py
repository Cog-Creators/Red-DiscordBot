from .controller import ControllerCommands
from .miscellaneous import MiscellaneousCommands
from .player import PlayerCommands
from .audioset import AudioSetCommands
from .equalizer import EqualizerCommands
from .llset import LavalinkSetCommands
from .localtracks import LocalTracksCommands
from .playlists import PlayListCommands
from .queue import QueueCommands
from ..utils import CompositeMetaClass


class Commands(
    AudioSetCommands,
    ControllerCommands,
    EqualizerCommands,
    LavalinkSetCommands,
    LocalTracksCommands,
    MiscellaneousCommands,
    PlayerCommands,
    PlayListCommands,
    QueueCommands,
    metaclass=CompositeMetaClass,
):
    pass
