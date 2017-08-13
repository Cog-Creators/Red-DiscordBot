from core.bot import Red
from .cleanup import Cleanup
from .filter import Filter
from .mod import Mod


def setup(bot: Red):
    # Filter and Cleanup don't depend on ModLog so let's just add them (if they're not loaded)
    if not bot.get_cog("Cleanup"):
        bot.add_cog(Cleanup(bot))
    if not bot.get_cog("Filter"):
        bot.add_cog(Filter(bot))
    bot.add_cog(Mod(bot))
