from .economy import Economy
from core.bot import Red


def setup(bot: Red, from_delayed: bool=False):
    if not from_delayed:
        bot.delayed_load_extension("economy", ("bank",))
    else:
        bank = bot.get_cog("Bank")
        bot.add_cog(Economy(bot, bank))
