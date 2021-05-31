from redbot.core.bot import Red
from redbot.core.utils import get_end_user_data_statement

from .core import Audio

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


def setup(bot: Red):
    cog = Audio(bot)
    bot.add_cog(cog)
    cog.start_up_task()
