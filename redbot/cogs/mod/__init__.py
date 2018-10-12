from redbot.core.bot import Red
from .modcore import Mod

from .bans import KickBanMixin
from .mutes import MuteMixin
from .misc import MiscMixin
from .utils import UtilsMixin


async def setup(bot: Red):
    cog = Mod(bot)
    await cog._casetype_registration()
    bot.add_cog(Mod(bot))
