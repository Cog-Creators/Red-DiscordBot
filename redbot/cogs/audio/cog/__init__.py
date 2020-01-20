from redbot.core.bot import Red
from redbot.core.commands import Cog

from . import abc, cog_utils, commands, events, tasks, utilities
from .cog_utils import CompositeMetaClass


class Audio(
    commands.Commands,
    events.Events,
    tasks.Tasks,
    utilities.Utilities,
    Cog,
    metaclass=CompositeMetaClass,
):
    """Class joining all Audio subclasses"""

    def __init__(self, bot: Red):
        self.bot = bot
