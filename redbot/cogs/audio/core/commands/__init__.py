from ..cog_utils import CompositeMetaClass
from .audioset import AudioSetCommands
from .controller import PlayerControllerCommands
from .equalizer import EqualizerCommands
from .filters import EffectsCommands
from .localtracks import LocalTrackCommands
from .miscellaneous import MiscellaneousCommands
from .player import PlayerCommands
from .playlists import PlaylistCommands
from .queue import QueueCommands


class Commands(
    AudioSetCommands,
    PlayerControllerCommands,
    EqualizerCommands,
    EffectsCommands,
    LocalTrackCommands,
    MiscellaneousCommands,
    PlayerCommands,
    PlaylistCommands,
    QueueCommands,
    metaclass=CompositeMetaClass,
):
    """Class joining all command subclasses"""
