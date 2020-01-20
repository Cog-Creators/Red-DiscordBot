from .equalizer import EqualizerUtilities
from .formatting import FormattingUtilities
from .local_tracks import LocalTrackUtilities
from .miscellaneous import MiscellaneousUtilities
from .player import PlayerUtilities
from .queue import QueueUtilities
from .validation import ValidationUtilities
from ..cog_utils import CompositeMetaClass


class Utilities(
    EqualizerUtilities,
    FormattingUtilities,
    LocalTrackUtilities,
    MiscellaneousUtilities,
    PlayerUtilities,
    QueueUtilities,
    ValidationUtilities,
    metaclass=CompositeMetaClass,
):
    """Class joining all utility subclasses"""
