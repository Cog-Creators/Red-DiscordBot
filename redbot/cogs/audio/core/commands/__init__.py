from ..cog_utils import CompositeMetaClass
from .audioset import AudioSetCommands
from .controller import PlayerControllerCommands
from .equalizer import EqualizerCommands
from .llset import LavalinkSetupCommands
from .localtracks import LocalTrackCommands
from .miscellaneous import MiscellaneousCommands
from .player import PlayerCommands
from .playlists import PlaylistCommands
from .queue import QueueCommands
from redbot.core.i18n import Translator, cog_i18n


_ = Translator("Audio", __file__)


@cog_i18n(_)
class Commands(
    AudioSetCommands,
    PlayerControllerCommands,
    EqualizerCommands,
    LavalinkSetupCommands,
    LocalTrackCommands,
    MiscellaneousCommands,
    PlayerCommands,
    PlaylistCommands,
    QueueCommands,
    metaclass=CompositeMetaClass,
):
    """Play audio through voice channels."""
