from cogs.modlog import ModLog
from core.bot import Red
from .cleanup import Cleanup
from .filter import Filter
from .mod import Mod


def setup(bot: Red, from_delayed: bool=False):
    # Filter and Cleanup don't depend on ModLog so let's just add them (if they're not loaded)
    if not bot.get_cog("Cleanup"):
        bot.add_cog(Cleanup(bot))
    if not bot.get_cog("Filter"):
        bot.add_cog(Filter(bot))
    if from_delayed or isinstance(bot.get_cog("ModLog"), ModLog):
        modlog = bot.get_cog("ModLog")
        bot.add_cog(Mod(bot, modlog))
    else:
        bot.delayed_load_extension("mod", ("modlog",))
